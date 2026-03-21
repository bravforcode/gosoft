from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import redis_client
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import models
from app.db.crud import alert_crud, event_crud, product_crud
from app.db.schemas import AlertCreate, DetectionEventCreate
from app.services.notification_service import notification_service
from app.services.reorder_service import reorder_service
from app.vision.types import DetectionResult, ZoneAnalysis
from app.websocket.events import SIVEvent


logger = get_logger("services.alert")


class AlertService:
    async def process_detection(self, db: AsyncSession, detection: DetectionResult) -> list[models.Alert]:
        alerts: list[models.Alert] = []
        for zone_id, zone in detection.zones.items():
            product = await self._resolve_product(db, zone_id, detection.camera_id)
            if not product:
                continue
            event_type, severity = self._event_type_from_zone(zone)
            event = await event_crud.create(
                db,
                obj_in=DetectionEventCreate(
                    camera_id=detection.camera_id,
                    product_id=product.id,
                    zone=zone_id,
                    event_type=event_type,
                    severity=severity,
                    fullness_before=max(0.0, float(zone.fullness_score) - 0.15),
                    fullness_after=zone.fullness_score,
                    confidence=zone.confidence,
                    bbox_data={"bbox": zone.bbox},
                    metadata={"anomalies": zone.anomalies, "stage": detection.stage_used},
                ),
            )
            if not await self._should_create_alert(db, product.id, severity):
                continue
            alert = await alert_crud.create(
                db,
                obj_in=AlertCreate(
                    event_id=event.id,
                    product_id=product.id,
                    camera_id=detection.camera_id,
                    title=self._title_for_zone(product, zone),
                    description=f"{product.name_en} in {zone_id} is {zone.status}.",
                    severity=severity,
                    status=models.AlertStatus.ACTIVE,
                    evidence_frame_path=event.frame_path,
                ),
            )
            alerts.append(alert)
            await redis_client.publish(
                "siv:events",
                SIVEvent(
                    type="alert_created",
                    camera_id=detection.camera_id,
                    zone=zone_id,
                    product_id=product.id,
                    sku=product.sku,
                    severity=severity,
                    data={"alert_id": alert.id, "title": alert.title},
                    session_id="server-session",
                ).model_dump(mode="json"),
            )
            await reorder_service.check_and_create_po(db, product.id, product.current_stock)
            if severity == models.Severity.CRITICAL:
                await notification_service.send_alert(alert, product)
        return alerts

    async def auto_resolve_check(self, db: AsyncSession, zone: str, camera_id: str, fullness: float) -> list[models.Alert]:
        if fullness < get_settings().STOCK_LOW_THRESHOLD:
            return []
        statement = select(models.Alert).join(models.Product).where(
            models.Alert.camera_id == camera_id,
            models.Product.zone_id == zone,
            models.Alert.status.in_([models.AlertStatus.ACTIVE, models.AlertStatus.ACKNOWLEDGED]),
        )
        result = await db.execute(statement)
        alerts = list(result.scalars().all())
        resolved: list[models.Alert] = []
        for alert in alerts:
            alert.status = models.AlertStatus.AUTO_RESOLVED
            alert.auto_resolved_at = datetime.utcnow()
            db.add(alert)
            resolved.append(alert)
            await redis_client.publish(
                "siv:events",
                SIVEvent(
                    type="alert_resolved",
                    camera_id=camera_id,
                    zone=zone,
                    product_id=alert.product_id,
                    severity=alert.severity,
                    data={"alert_id": alert.id},
                    session_id="server-session",
                ).model_dump(mode="json"),
            )
        await db.commit()
        return resolved

    def _event_type_from_zone(self, zone: ZoneAnalysis) -> tuple[models.EventType, models.Severity]:
        if zone.status == "empty":
            return models.EventType.EMPTY_SHELF, models.Severity.CRITICAL
        if zone.status == "critical":
            return models.EventType.STOCK_UPDATE, models.Severity.CRITICAL
        if zone.status == "low":
            return models.EventType.STOCK_UPDATE, models.Severity.WARNING
        if zone.anomalies:
            return models.EventType.ANOMALY, models.Severity.WARNING
        return models.EventType.STOCK_UPDATE, models.Severity.INFO

    async def _resolve_product(self, db: AsyncSession, zone_id: str, camera_id: str) -> models.Product | None:
        statement = select(models.Product).where(models.Product.zone_id == zone_id, models.Product.camera_id == camera_id)
        result = await db.execute(statement)
        return result.scalars().first()

    async def _should_create_alert(self, db: AsyncSession, product_id: str, severity: models.Severity) -> bool:
        if severity == models.Severity.INFO:
            return False
        statement = select(models.Alert).where(
            models.Alert.product_id == product_id,
            models.Alert.status.in_([models.AlertStatus.ACTIVE, models.AlertStatus.ACKNOWLEDGED]),
            models.Alert.created_at >= datetime.utcnow() - timedelta(minutes=10),
        )
        result = await db.execute(statement)
        existing = result.scalars().first()
        return existing is None

    def _title_for_zone(self, product: models.Product, zone: ZoneAnalysis) -> str:
        if zone.status == "empty":
            return f"Stock Empty - {product.name_en}"
        if zone.status == "critical":
            return f"Critical Stock - {product.name_en}"
        return f"Low Stock - {product.name_en}"


alert_service = AlertService()
