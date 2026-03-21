from __future__ import annotations

import asyncio
import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.exceptions import error_response
from app.db.crud import camera_crud, event_crud
from app.db.database import get_db
from app.db.models import User, UserRole
from app.db.schemas import CameraDetail, CameraStatusResponse, CameraUpdate, ConnectionTestResult, SnapshotResult
from app.vision.camera_manager import camera_manager


router = APIRouter(prefix="/cameras", tags=["cameras"])
stream_router = APIRouter(prefix="/stream", tags=["streams"])


@router.get("", response_model=list[CameraStatusResponse])
async def get_cameras(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> list[CameraStatusResponse]:
    cameras = await camera_crud.get_multi(db, limit=100)
    items = []
    recent_events = await event_crud.get_recent(db, minutes=60)
    by_camera: dict[str, list] = {}
    for event in recent_events:
        by_camera.setdefault(event.camera_id, []).append(event)
    for camera in cameras:
        events = by_camera.get(camera.id, [])
        items.append(
            CameraStatusResponse.model_validate(
                {
                    **camera.__dict__,
                    "detections_last_minute": len(events),
                    "avg_confidence": round(
                        sum(float(event.confidence) for event in events) / max(1, len(events)),
                        2,
                    ),
                }
            )
        )
    return items


@router.get("/{camera_id}", response_model=CameraDetail)
async def get_camera_detail(camera_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> CameraDetail:
    camera = await camera_crud.get(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail=error_response("camera_not_found", "Camera not found.", {"camera_id": camera_id}))
    recent_events = [event for event in await event_crud.get_recent(db, minutes=30) if event.camera_id == camera_id]
    return CameraDetail.model_validate(
        {
            **camera.__dict__,
            "detections_last_minute": len(recent_events),
            "avg_confidence": round(sum(float(event.confidence) for event in recent_events) / max(1, len(recent_events)), 2),
            "current_detections": recent_events,
            "stats": camera_manager.stats.get(camera_id).__dict__ if camera_id in camera_manager.stats else {},
        }
    )


@router.post("/{camera_id}/snapshot", response_model=SnapshotResult)
async def snapshot_camera(camera_id: str, _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))) -> SnapshotResult:
    frame = await camera_manager.get_latest_frame(camera_id)
    if not frame:
        raise HTTPException(status_code=404, detail=error_response("frame_unavailable", "No frame available.", {"camera_id": camera_id}))
    directory = Path("data/evidence") / camera_id / datetime.utcnow().strftime("%Y-%m-%d")
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / f"{datetime.utcnow().strftime('%H%M%S')}_snapshot.jpg"
    cv2.imwrite(str(file_path), frame.data, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return SnapshotResult(camera_id=camera_id, file_path=str(file_path), captured_at=datetime.utcnow())


@router.post("/{camera_id}/test", response_model=ConnectionTestResult)
async def test_camera_connection(camera_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))) -> ConnectionTestResult:
    start = datetime.utcnow()
    camera = await camera_crud.get(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail=error_response("camera_not_found", "Camera not found.", {"camera_id": camera_id}))
    cap = cv2.VideoCapture(int(camera.stream_url) if camera.stream_url.isdigit() else camera.stream_url)
    ok, _ = cap.read()
    cap.release()
    latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
    return ConnectionTestResult(ok=ok, latency_ms=latency_ms, message="Connection ok" if ok else "Unable to read frame")


@router.put("/{camera_id}/config", response_model=CameraDetail)
async def update_camera_config(
    camera_id: str,
    payload: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> CameraDetail:
    camera = await camera_crud.get(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail=error_response("camera_not_found", "Camera not found.", {"camera_id": camera_id}))
    await camera_crud.update(db, db_obj=camera, obj_in=payload)
    return await get_camera_detail(camera_id, db)


@router.get("/{camera_id}/frames")
async def stream_frame_thumbnails(camera_id: str, _: User = Depends(get_current_user)) -> StreamingResponse:
    async def generator():
        worker = camera_manager.cameras.get(camera_id)
        if not worker:
            return
        while True:
            frames = list(worker.buffer)[-5:]
            for frame in frames:
                success, buffer = cv2.imencode(".jpg", frame.data, [cv2.IMWRITE_JPEG_QUALITY, 60])
                if not success:
                    continue
                payload = base64.b64encode(buffer.tobytes()).decode("utf-8")
                yield (payload + "\n").encode("utf-8")
            await asyncio.sleep(2)

    return StreamingResponse(generator(), media_type="application/x-ndjson")


@stream_router.get("/{camera_id}")
async def stream_with_overlay(camera_id: str) -> StreamingResponse:
    return StreamingResponse(
        camera_manager.get_mjpeg_stream(camera_id, overlay=True),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@stream_router.get("/{camera_id}/raw")
async def stream_raw(camera_id: str) -> StreamingResponse:
    return StreamingResponse(
        camera_manager.get_mjpeg_stream(camera_id, overlay=False),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
