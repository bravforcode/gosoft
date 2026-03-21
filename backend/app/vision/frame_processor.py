from __future__ import annotations

import asyncio
from pathlib import Path

import cv2

from app.cache.redis_client import redis_client
from app.core.logging import get_logger
from app.db.crud import product_crud
from app.db.database import AsyncSessionLocal
from app.services.alert_service import alert_service
from app.vision.camera_manager import CameraManager, camera_manager
from app.vision.shelf_detector import ShelfDetector
from app.websocket.events import SIVEvent


logger = get_logger("vision.frame_processor")


class FrameProcessor:
    def __init__(self, camera_manager_instance: CameraManager | None = None, detector: ShelfDetector | None = None) -> None:
        self.camera_manager = camera_manager_instance or camera_manager
        self.detector = detector or ShelfDetector()
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._last_zone_state: dict[str, dict[str, float]] = {}
        self._last_triggered: dict[str, float] = {}

    async def start(self) -> None:
        for camera_id in self.camera_manager.cameras.keys():
            self.detector.configure_zones(camera_id)
            self._tasks[camera_id] = asyncio.create_task(self._run_camera(camera_id))

    async def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    async def _run_camera(self, camera_id: str) -> None:
        while True:
            frame = await self.camera_manager.get_latest_frame(camera_id)
            if not frame:
                await asyncio.sleep(0.2)
                continue
            result = self.detector.analyze_frame(camera_id, frame.data)
            self.camera_manager.register_detection(result)
            significant = self._is_significant(camera_id, result)
            if significant:
                async with AsyncSessionLocal() as db:
                    for zone_id, zone in result.zones.items():
                        await self._update_inventory(db, camera_id, zone_id, zone.fullness_score)
                    await alert_service.process_detection(db, result)
                    for zone_id, zone in result.zones.items():
                        await alert_service.auto_resolve_check(db, zone_id, camera_id, zone.fullness_score)
                await redis_client.publish(
                    "siv:events",
                    SIVEvent(
                        type="stock_update",
                        camera_id=camera_id,
                        severity=self._worst_severity(result),
                        data={
                            "avg_fullness": result.global_stats["avg_fullness"],
                            "zones": {zone_id: zone.fullness_score for zone_id, zone in result.zones.items()},
                        },
                        session_id="server-session",
                    ).model_dump(mode="json"),
                )
            await asyncio.sleep(0.5)

    async def _update_inventory(self, db, camera_id: str, zone_id: str, fullness: float) -> None:
        from sqlalchemy import select
        from app.db import models

        statement = select(models.Product).where(models.Product.camera_id == camera_id, models.Product.zone_id == zone_id)
        result = await db.execute(statement)
        product = result.scalars().first()
        if not product:
            return
        new_stock = max(0, min(product.max_capacity, int(round(product.max_capacity * fullness))))
        await product_crud.update_stock(db, product.id, new_stock)

    def _is_significant(self, camera_id: str, result) -> bool:
        current_state = {zone_id: zone.fullness_score for zone_id, zone in result.zones.items()}
        previous_state = self._last_zone_state.get(camera_id, {})
        significant = False
        for zone_id, fullness in current_state.items():
            previous = previous_state.get(zone_id)
            if previous is None or abs(fullness - previous) > 0.15:
                significant = True
        if result.persons_detected or any(zone.anomalies for zone in result.zones.values()):
            significant = True
        self._last_zone_state[camera_id] = current_state
        return significant

    def _worst_severity(self, result) -> object:
        from app.db.models import Severity

        statuses = [zone.status for zone in result.zones.values()]
        if "empty" in statuses or "critical" in statuses:
            return Severity.CRITICAL
        if "low" in statuses:
            return Severity.WARNING
        return Severity.INFO


frame_processor = FrameProcessor()
