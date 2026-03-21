from __future__ import annotations

import asyncio
from datetime import datetime
from random import choice

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.cache.redis_client import redis_client
from app.core.config import get_settings
from app.core.exceptions import error_response
from app.db import models
from app.db.crud import alert_crud, event_crud, po_crud, product_crud
from app.db.database import get_db
from app.db.models import User, UserRole
from app.db.schemas import AlertCreate, DetectionEventCreate
from app.services.reorder_service import reorder_service
from app.websocket.events import SIVEvent


router = APIRouter(prefix="/demo", tags=["demo"])
demo_state = {"running": False, "last_scenario": None, "started_at": None, "events_emitted": 0}


def ensure_demo_access(current_user: User) -> None:
    settings = get_settings()
    if settings.DEMO_MODE or current_user.role == UserRole.ADMIN:
        return
    raise HTTPException(status_code=403, detail=error_response("demo_disabled", "Demo mode is disabled."))


@router.get("/status")
async def get_demo_status(current_user: User = Depends(get_current_user)) -> dict:
    ensure_demo_access(current_user)
    return demo_state


@router.post("/reset")
async def reset_demo(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    ensure_demo_access(current_user)
    await db.execute(delete(models.PurchaseOrder))
    await db.execute(delete(models.Alert))
    await db.execute(delete(models.DetectionEvent))
    products = await product_crud.get_multi(db, limit=500)
    for product in products:
        product.current_stock = product.max_capacity
        db.add(product)
    await db.commit()
    demo_state.update({"running": False, "last_scenario": "reset", "started_at": None, "events_emitted": 0})
    return {"ok": True}


@router.post("/inject/{scenario}")
async def inject_scenario(
    scenario: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ensure_demo_access(current_user)
    handler = getattr(_DemoScenarioRunner(db), f"scenario_{scenario}", None)
    if not handler:
        raise HTTPException(status_code=404, detail=error_response("scenario_not_found", "Unknown demo scenario.", {"scenario": scenario}))
    result = await handler()
    demo_state["last_scenario"] = scenario
    return result


@router.post("/full-scenario")
async def run_full_scenario(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    ensure_demo_access(current_user)
    runner = _DemoScenarioRunner(db)
    demo_state.update({"running": True, "last_scenario": "full-scenario", "started_at": datetime.utcnow().isoformat(), "events_emitted": 0})
    await reset_demo(db, current_user)
    await asyncio.sleep(5)
    await runner.emit_heartbeat()
    await asyncio.sleep(5)
    await runner.scenario_empty_shelf()
    await asyncio.sleep(10)
    await runner.scenario_motion_anomaly()
    await asyncio.sleep(10)
    await runner.scenario_planogram_violation()
    await asyncio.sleep(10)
    await runner.scenario_vendor_delivery()
    await asyncio.sleep(10)
    await runner.scenario_restock_complete()
    await asyncio.sleep(10)
    await runner.scenario_rapid_stock_drop()
    await asyncio.sleep(30)
    demo_state["running"] = False
    return {"ok": True, "status": demo_state}


class _DemoScenarioRunner:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def scenario_empty_shelf(self) -> dict:
        product = await self._pick_product()
        product.current_stock = max(0, int(product.max_capacity * 0.05))
        self.db.add(product)
        await self.db.commit()
        event = await event_crud.create(
            self.db,
            obj_in=DetectionEventCreate(
                camera_id=product.camera_id,
                product_id=product.id,
                zone=product.zone_id,
                event_type=models.EventType.EMPTY_SHELF,
                severity=models.Severity.CRITICAL,
                fullness_before=0.40,
                fullness_after=0.05,
                confidence=0.97,
                metadata={"scenario": "empty_shelf"},
            ),
        )
        alert = await alert_crud.create(
            self.db,
            obj_in=AlertCreate(
                event_id=event.id,
                product_id=product.id,
                camera_id=product.camera_id,
                title=f"Critical empty shelf - {product.name_en}",
                description=f"{product.name_en} is nearly empty in {product.zone_id}.",
                severity=models.Severity.CRITICAL,
                status=models.AlertStatus.ACTIVE,
            ),
        )
        po = await reorder_service.check_and_create_po(self.db, product.id, product.current_stock)
        await self._publish(
            "alert_created",
            camera_id=product.camera_id,
            zone=product.zone_id,
            product_id=product.id,
            sku=product.sku,
            severity=models.Severity.CRITICAL,
            data={"alert_id": alert.id, "po_id": po.id if po else None},
        )
        return {"ok": True, "alert_id": alert.id, "po_id": po.id if po else None}

    async def scenario_motion_anomaly(self) -> dict:
        product = await self._pick_product()
        event = await event_crud.create(
            self.db,
            obj_in=DetectionEventCreate(
                camera_id=product.camera_id,
                product_id=product.id,
                zone="D-02",
                event_type=models.EventType.ANOMALY,
                severity=models.Severity.WARNING,
                fullness_before=0.80,
                fullness_after=0.75,
                confidence=0.89,
                metadata={"anomaly_type": "unusual_movement", "duration_seconds": 8},
            ),
        )
        alert = await alert_crud.create(
            self.db,
            obj_in=AlertCreate(
                event_id=event.id,
                product_id=product.id,
                camera_id=product.camera_id,
                title="Motion Anomaly Detected - Zone D",
                description="Unexpected movement detected near shelf zone.",
                severity=models.Severity.WARNING,
                status=models.AlertStatus.ACTIVE,
            ),
        )
        await self._publish("anomaly_detected", camera_id=product.camera_id, zone="D-02", severity=models.Severity.WARNING, data={"alert_id": alert.id})
        return {"ok": True, "alert_id": alert.id}

    async def scenario_planogram_violation(self) -> dict:
        product = await self._pick_product()
        event = await event_crud.create(
            self.db,
            obj_in=DetectionEventCreate(
                camera_id=product.camera_id,
                product_id=product.id,
                zone=product.zone_id,
                event_type=models.EventType.PLANOGRAM_VIOLATION,
                severity=models.Severity.INFO,
                fullness_before=0.65,
                fullness_after=0.62,
                confidence=0.92,
                metadata={"compliance_score": 0.62, "misplaced_products": 3, "reference_match": 62},
            ),
        )
        await self._publish("stock_update", camera_id=product.camera_id, zone=product.zone_id, severity=models.Severity.INFO, data={"event_id": event.id})
        return {"ok": True, "event_id": event.id}

    async def scenario_restock_complete(self) -> dict:
        product = await self._pick_product(low_only=True)
        product.current_stock = int(product.max_capacity * 0.90)
        self.db.add(product)
        await self.db.commit()
        await self._publish(
            "restock_confirmed",
            camera_id=product.camera_id,
            zone=product.zone_id,
            product_id=product.id,
            sku=product.sku,
            severity=models.Severity.INFO,
            data={"units_added": int(product.max_capacity * 0.85)},
        )
        return {"ok": True}

    async def scenario_vendor_delivery(self) -> dict:
        product = await self._pick_product()
        event = await event_crud.create(
            self.db,
            obj_in=DetectionEventCreate(
                camera_id=product.camera_id,
                product_id=product.id,
                zone=product.zone_id,
                event_type=models.EventType.DELIVERY,
                severity=models.Severity.WARNING,
                fullness_before=0.10,
                fullness_after=0.68,
                confidence=0.88,
                metadata={"expected_units": 48, "detected_units": 42},
            ),
        )
        alert = await alert_crud.create(
            self.db,
            obj_in=AlertCreate(
                event_id=event.id,
                product_id=product.id,
                camera_id=product.camera_id,
                title="Delivery discrepancy detected",
                description="Detected delivered quantity differs from PO quantity.",
                severity=models.Severity.WARNING,
                status=models.AlertStatus.ACTIVE,
            ),
        )
        await self._publish("alert_created", camera_id=product.camera_id, zone=product.zone_id, severity=models.Severity.WARNING, data={"alert_id": alert.id})
        return {"ok": True}

    async def scenario_rapid_stock_drop(self) -> dict:
        product = await self._pick_product()
        for fullness in [0.80, 0.71, 0.62, 0.53, 0.44, 0.35]:
            product.current_stock = int(product.max_capacity * fullness)
            self.db.add(product)
            await self.db.commit()
            await self._publish(
                "stock_update",
                camera_id=product.camera_id,
                zone=product.zone_id,
                product_id=product.id,
                sku=product.sku,
                severity=models.Severity.CRITICAL if fullness <= 0.35 else models.Severity.WARNING,
                data={"fullness": fullness},
            )
            await asyncio.sleep(5)
        return {"ok": True}

    async def emit_heartbeat(self) -> None:
        await self._publish("heartbeat", severity=models.Severity.INFO, data={"frame_count": 1, "events_min": 0})

    async def _pick_product(self, low_only: bool = False) -> models.Product:
        products = await product_crud.get_multi(self.db, limit=500)
        if low_only:
            low_products = [product for product in products if product.current_stock <= product.reorder_threshold]
            if low_products:
                return choice(low_products)
        return choice(products)

    async def _publish(self, event_type: str, **payload) -> None:
        await redis_client.publish("siv:events", SIVEvent(type=event_type, session_id="server-session", **payload).model_dump(mode="json"))
        demo_state["events_emitted"] += 1
