from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO

from app.core.config import get_settings
from app.core.logging import get_logger
from app.vision.claude_vision import ZoneImage, claude_vision_service
from app.vision.types import DetectionResult, MotionEvent, ZoneAnalysis


logger = get_logger("vision.shelf_detector")


@dataclass
class ZoneConfig:
    grid_cols: int
    grid_rows: int
    roi: tuple[int, int, int, int] | None = None


@dataclass
class YOLODetection:
    class_id: int
    confidence: float
    bbox: tuple[int, int, int, int]
    label: str


class ShelfDetector:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.yolo_model: YOLO | None = None
        self.bg_subtractors: dict[str, cv2.BackgroundSubtractor] = {}
        self.zone_configs: dict[str, ZoneConfig] = {}
        self.calibration_baselines: dict[str, float] = {}
        self.frame_counters: dict[str, int] = {}

    def configure_zones(self, camera_id: str, grid_cols: int = 5, grid_rows: int = 3, roi: tuple | None = None) -> None:
        self.zone_configs[camera_id] = ZoneConfig(grid_cols=grid_cols, grid_rows=grid_rows, roi=roi)

    def calibrate(self, camera_id: str, full_shelf_frame: np.ndarray) -> None:
        self.configure_zones(camera_id)
        config = self.zone_configs[camera_id]
        x1, y1, x2, y2 = config.roi or (0, 0, full_shelf_frame.shape[1], full_shelf_frame.shape[0])
        roi_frame = full_shelf_frame[y1:y2, x1:x2]
        baseline = self._compute_zone_fullness(roi_frame, None)
        self.calibration_baselines[camera_id] = baseline
        calibration_dir = Path("data")
        calibration_dir.mkdir(parents=True, exist_ok=True)
        calibration_file = calibration_dir / f"{camera_id}_baseline.json"
        calibration_file.write_text(json.dumps({"baseline": baseline}), encoding="utf-8")

    def analyze_frame(self, camera_id: str, frame: np.ndarray) -> DetectionResult:
        start = time.perf_counter()
        if camera_id not in self.zone_configs:
            self.configure_zones(camera_id)
        config = self.zone_configs[camera_id]
        self.frame_counters[camera_id] = self.frame_counters.get(camera_id, 0) + 1
        cols, rows = config.grid_cols, config.grid_rows
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = config.roi or (0, 0, w, h)
        roi_frame = frame[y1:y2, x1:x2]
        zone_w = max(1, (x2 - x1) // cols)
        zone_h = max(1, (y2 - y1) // rows)
        baseline = self.calibration_baselines.get(camera_id)

        zones: dict[str, ZoneAnalysis] = {}
        for row in range(rows):
            for col in range(cols):
                zx1 = col * zone_w
                zy1 = row * zone_h
                zx2 = x2 - x1 if col == cols - 1 else (col + 1) * zone_w
                zy2 = y2 - y1 if row == rows - 1 else (row + 1) * zone_h
                crop = roi_frame[zy1:zy2, zx1:zx2]
                fullness = self._compute_zone_fullness(crop, baseline)
                status = self._map_status(fullness)
                zone_id = f"{chr(65 + col)}-{row + 1:02d}"
                zones[zone_id] = ZoneAnalysis(
                    zone_id=zone_id,
                    fullness_score=fullness,
                    status=status,
                    product_count=max(0, int(fullness * 10)),
                    confidence=round(0.78 + min(0.2, fullness * 0.2), 2),
                    bbox=(x1 + zx1, y1 + zy1, x1 + zx2, y1 + zy2),
                    anomalies=[],
                )

        raw_detections: list[dict[str, Any]] = []
        persons_detected = 0
        stage_used = "heuristic"
        if self.frame_counters[camera_id] % max(1, self.settings.CLAUDE_ANALYSIS_INTERVAL) == 0:
            detections = self._detect_yolo(frame)
            raw_detections = [det.__dict__ for det in detections]
            stage_used = "yolo"
            for detection in detections:
                if detection.class_id == 0:
                    persons_detected += 1
                zone_id = self._bbox_to_zone(detection.bbox, zones)
                if zone_id:
                    zone = zones[zone_id]
                    zone.product_count += 1
                    zone.products_detected.append(detection.label)
                    if detection.class_id == 0:
                        zone.anomalies.append("person_detected")
                        zone.status = "critical" if zone.status == "ok" else zone.status

        motion_events = self._detect_motion(camera_id, roi_frame, zones)
        if motion_events:
            for motion in motion_events:
                zones[motion.zone_id].anomalies.append("motion_anomaly")

        elapsed_ms = (time.perf_counter() - start) * 1000
        global_stats = {
            "avg_fullness": round(sum(zone.fullness_score for zone in zones.values()) / max(1, len(zones)), 3),
            "zones_empty": sum(1 for zone in zones.values() if zone.status == "empty"),
            "zones_critical": sum(1 for zone in zones.values() if zone.status == "critical"),
        }
        return DetectionResult(
            camera_id=camera_id,
            zones=zones,
            global_stats=global_stats,
            persons_detected=persons_detected,
            motion_events=motion_events,
            processing_time_ms=elapsed_ms,
            stage_used=stage_used,
            raw_detections=raw_detections,
        )

    def _compute_zone_fullness(self, zone_crop: np.ndarray, baseline: float | None) -> float:
        if zone_crop.size == 0:
            return 0.0
        gray = cv2.cvtColor(zone_crop, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray) / 255.0)

        lab = cv2.cvtColor(zone_crop, cv2.COLOR_BGR2LAB)
        color_var = float(np.std(lab[:, :, 1]) + np.std(lab[:, :, 2]))
        color_var_norm = min(color_var / 50.0, 1.0)

        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0) / edges.size)
        edge_norm = min(edge_density / 0.2, 1.0)

        score = 0.65 * brightness + 0.2 * color_var_norm + 0.15 * edge_norm
        if baseline and baseline > 0:
            score = min(1.0, score / baseline)
        return max(0.0, min(1.0, score))

    def _detect_yolo(self, frame: np.ndarray) -> list[YOLODetection]:
        if self.yolo_model is None:
            self.yolo_model = YOLO(self.settings.YOLO_MODEL_PATH)
        results = self.yolo_model.predict(frame, verbose=False, conf=self.settings.YOLO_CONFIDENCE_THRESHOLD)
        detections: list[YOLODetection] = []
        allowed_classes = {0, 39, 40, 41, 45}
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                if class_id not in allowed_classes:
                    continue
                x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
                detections.append(
                    YOLODetection(
                        class_id=class_id,
                        confidence=float(box.conf[0].item()),
                        bbox=(x1, y1, x2, y2),
                        label=result.names[class_id],
                    )
                )
        return detections

    async def _analyze_with_claude(self, camera_id: str, zone: str, zone_crop: np.ndarray) -> dict[str, Any] | None:
        results = await claude_vision_service.analyze_zones([ZoneImage(camera_id=camera_id, zone_id=zone, image=zone_crop)])
        return results[0].__dict__ if results else None

    def _detect_motion(self, camera_id: str, frame: np.ndarray, zones: dict[str, ZoneAnalysis]) -> list[MotionEvent]:
        subtractor = self.bg_subtractors.setdefault(camera_id, cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=32))
        fg_mask = subtractor.apply(frame)
        motion_ratio = float(np.sum(fg_mask > 0) / fg_mask.size)
        if motion_ratio < 0.06:
            return []
        hottest_zone = max(zones.values(), key=lambda zone: zone.fullness_score)
        return [MotionEvent(zone_id=hottest_zone.zone_id, movement_score=motion_ratio, detected_at=time_to_datetime())]

    def _map_status(self, fullness: float) -> str:
        if fullness < self.settings.STOCK_EMPTY_THRESHOLD:
            return "empty"
        if fullness < self.settings.STOCK_CRITICAL_THRESHOLD:
            return "critical"
        if fullness < self.settings.STOCK_LOW_THRESHOLD:
            return "low"
        return "ok"

    def _bbox_to_zone(self, bbox: tuple[int, int, int, int], zones: dict[str, ZoneAnalysis]) -> str | None:
        cx = (bbox[0] + bbox[2]) // 2
        cy = (bbox[1] + bbox[3]) // 2
        for zone_id, zone in zones.items():
            x1, y1, x2, y2 = zone.bbox
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                return zone_id
        return None


def time_to_datetime() -> Any:
    from datetime import datetime

    return datetime.utcnow()
