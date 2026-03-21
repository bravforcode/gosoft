from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.db.models import Severity


EventName = Literal[
    "stock_update",
    "alert_created",
    "alert_resolved",
    "reorder_triggered",
    "anomaly_detected",
    "camera_status",
    "po_approved",
    "restock_confirmed",
    "heartbeat",
]


class SIVEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: EventName
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    camera_id: str | None = None
    zone: str | None = None
    product_id: str | None = None
    sku: str | None = None
    severity: Severity = Severity.INFO
    data: dict[str, Any] = Field(default_factory=dict)
    session_id: str
