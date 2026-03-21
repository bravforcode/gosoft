from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import cv2
import numpy as np

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.vision.types import DetectionResult, Frame


logger = get_logger("vision.camera_manager")


@dataclass
class CameraStats:
    status: str = "offline"
    last_frame_at: datetime | None = None
    fps_actual: float = 0.0
    frames_captured: int = 0
    reconnect_count: int = 0


class CameraWorker:
    def __init__(self, camera_id: str, url: str, display_fps: float = 25.0) -> None:
        self.camera_id = camera_id
        self.url = url
        self.display_fps = display_fps
        self.buffer: deque[Frame] = deque(maxlen=30)
        self.stats = CameraStats(status="connecting")
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._frame_number = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name=f"camera-{self.camera_id}")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def latest_frame(self) -> Frame | None:
        with self._lock:
            return self.buffer[-1] if self.buffer else None

    def _open_capture(self, url: str) -> cv2.VideoCapture:
        source: int | str = int(url) if url.isdigit() else url
        cap = cv2.VideoCapture(source)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _capture_loop(self) -> None:
        backoff = 2.0
        while not self._stop_event.is_set():
            capture = self._open_capture(self.url)
            if not capture.isOpened():
                self.stats.status = "offline"
                self.stats.reconnect_count += 1
                time.sleep(min(backoff, 60.0))
                backoff = min(backoff * 2, 60.0)
                continue
            self.stats.status = "online"
            backoff = 2.0
            last_tick = time.perf_counter()
            frames_since_tick = 0
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    self.stats.status = "offline"
                    break
                now = datetime.utcnow()
                self._frame_number += 1
                h, w = frame.shape[:2]
                item = Frame(
                    camera_id=self.camera_id,
                    data=frame,
                    timestamp=now,
                    frame_number=self._frame_number,
                    width=w,
                    height=h,
                )
                with self._lock:
                    self.buffer.append(item)
                self.stats.last_frame_at = now
                self.stats.frames_captured += 1
                frames_since_tick += 1
                elapsed = time.perf_counter() - last_tick
                if elapsed >= 1.0:
                    self.stats.fps_actual = frames_since_tick / elapsed
                    last_tick = time.perf_counter()
                    frames_since_tick = 0
                time.sleep(max(0.0, 1.0 / max(1.0, self.display_fps) - 0.001))
            capture.release()


class CameraManager:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.cameras: dict[str, CameraWorker] = {}
        self.last_detections: dict[str, DetectionResult] = {}
        self.stats: dict[str, CameraStats] = {}

    async def initialize(self) -> None:
        for config in self.settings.configured_cameras:
            worker = CameraWorker(config["id"], config["url"], display_fps=self.settings.CAMERA_DISPLAY_FPS)
            worker.start()
            self.cameras[config["id"]] = worker
            self.stats[config["id"]] = worker.stats
        logger.info("camera_manager_initialized", cameras=list(self.cameras.keys()))

    async def shutdown(self) -> None:
        for worker in self.cameras.values():
            worker.stop()

    async def get_latest_frame(self, camera_id: str) -> Frame | None:
        worker = self.cameras.get(camera_id)
        if not worker:
            return None
        return worker.latest_frame()

    async def get_mjpeg_stream(self, camera_id: str, overlay: bool = True):
        while True:
            frame = await self.get_latest_frame(camera_id)
            if not frame:
                await asyncio.sleep(0.2)
                continue
            image = frame.data.copy()
            if overlay and camera_id in self.last_detections:
                image = self.draw_detection_overlay(image, self.last_detections[camera_id])
            success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                await asyncio.sleep(0.04)
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            await asyncio.sleep(1.0 / max(1.0, self.settings.CAMERA_DISPLAY_FPS))

    def register_detection(self, result: DetectionResult) -> None:
        self.last_detections[result.camera_id] = result

    def draw_detection_overlay(self, frame: np.ndarray, detections: DetectionResult) -> np.ndarray:
        overlay = frame.copy()
        color_map = {
            "ok": (38, 188, 124),
            "low": (0, 191, 255),
            "critical": (0, 96, 255),
            "empty": (0, 0, 255),
        }
        for zone in detections.zones.values():
            x1, y1, x2, y2 = zone.bbox
            color = color_map.get(zone.status, (128, 128, 128))
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness=-1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness=2)
            label = f"{zone.zone_id} | {int(zone.fullness_score * 100)}%"
            cv2.putText(frame, label, (x1 + 8, y1 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

        for detection in detections.raw_detections:
            x1, y1, x2, y2 = detection["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 216, 0), 2)
            label = f"{detection['label']} • conf: {detection['confidence']:.2f}"
            cv2.putText(frame, label, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 216, 0), 1, cv2.LINE_AA)

        cv2.rectangle(frame, (0, frame.shape[0] - 28), (frame.shape[1], frame.shape[0]), (12, 16, 26), -1)
        cv2.putText(
            frame,
            f"YOLOv8n | {detections.processing_time_ms:.0f}ms | {len(detections.raw_detections)} det | {detections.camera_id}",
            (12, frame.shape[0] - 9),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (frame.shape[1] - 210, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        return frame


camera_manager = CameraManager()
