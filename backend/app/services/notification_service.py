from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Alert, Product, PurchaseOrder


logger = get_logger("services.notification")


class NotificationService:
    async def send_alert(self, alert: Alert, product: Product | None, channels: list[str] | None = None) -> None:
        channels = channels or ["websocket", "webhook", "line"]
        tasks = []
        if "webhook" in channels:
            tasks.append(self._send_webhook("alert", alert, product=product))
        if "line" in channels and get_settings().LINE_NOTIFY_TOKEN:
            tasks.append(self._send_line(alert, product))
        for task in tasks:
            try:
                await task
            except Exception as exc:
                logger.warning("notification_failed", channel="mixed", error=str(exc))

    async def send_po_created(self, po: PurchaseOrder) -> None:
        await self._send_webhook("purchase_order_created", po)

    async def send_delivery_confirmed(self, po: PurchaseOrder) -> None:
        await self._send_webhook("delivery_confirmed", po)

    async def send_system_health(self, stats: dict) -> None:
        await self._send_webhook("system_health", stats)

    async def _send_line(self, alert: Alert, product: Product | None) -> None:
        settings = get_settings()
        if not settings.LINE_NOTIFY_TOKEN:
            return
        product_name = product.name_th if product else alert.title
        message = (
            f"CRITICAL ALERT\n"
            f"สินค้า: {product_name}\n"
            f"Zone: {product.zone_id if product else '-'} | Camera: {alert.camera_id}\n"
            f"สถานะ: {alert.severity.value}\n"
            f"เวลา: {alert.created_at.isoformat()}"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://notify-api.line.me/api/notify",
                headers={"Authorization": f"Bearer {settings.LINE_NOTIFY_TOKEN}"},
                data={"message": message},
            )
            response.raise_for_status()
            logger.info("line_notification_sent", alert_id=alert.id)

    async def _send_webhook(self, event_type: str, payload_obj: object, **extra: object) -> None:
        settings = get_settings()
        if not settings.WEBHOOK_URL:
            return
        payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": json.loads(json.dumps(payload_obj, default=str)),
            "extra": extra,
        }
        body = json.dumps(payload, default=str).encode("utf-8")
        signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), body, hashlib.sha256).hexdigest()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-SIV-Signature": signature,
                },
            )
            response.raise_for_status()
            logger.info("webhook_sent", event_type=event_type)


notification_service = NotificationService()
