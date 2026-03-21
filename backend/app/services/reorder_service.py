from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import models
from app.db.crud import event_crud, po_crud, product_crud
from app.db.schemas import PurchaseOrderCreate
from app.services.erp_service import get_erp_adapter
from app.services.notification_service import notification_service


logger = get_logger("services.reorder")


class ReorderService:
    async def check_and_create_po(self, db: AsyncSession, product_id: str, current_stock: int) -> models.PurchaseOrder | None:
        product = await product_crud.get(db, product_id)
        if not product:
            return None
        if current_stock > product.reorder_threshold:
            return None
        existing = await po_crud.get_pending_by_product(db, product_id)
        if existing:
            return existing
        qty = await self._calculate_quantity(db, product)
        total_amount = Decimal(product.unit_cost) * qty
        po_id = await po_crud._next_po_id(db)
        po = await po_crud.create(
            db,
            obj_in=PurchaseOrderCreate(
                id=po_id,
                product_id=product.id,
                vendor_id=product.vendor_id,
                trigger_alert_id=None,
                quantity_ordered=qty,
                unit_cost=product.unit_cost,
                total_amount=total_amount,
                status=models.PurchaseOrderStatus.PENDING_APPROVAL,
                expected_delivery=datetime.utcnow() + timedelta(days=1),
                notes="Auto-generated from low stock threshold.",
            ),
        )
        if float(total_amount) < get_settings().AUTO_PO_APPROVAL_LIMIT:
            po = await self.approve_and_send(db, po.id, approved_by="system")
        await notification_service.send_po_created(po)
        return po

    async def approve_and_send(self, db: AsyncSession, po_id: str, approved_by: str) -> models.PurchaseOrder:
        po = await po_crud.approve(db, po_id, approved_by)
        if not po:
            raise ValueError("PO not found.")
        await self.send_to_vendor(db, po)
        return po

    async def send_to_vendor(self, db: AsyncSession, po: models.PurchaseOrder) -> bool:
        adapter = get_erp_adapter()
        try:
            if adapter:
                po.erp_po_number = await adapter.create_purchase_order(po)
                po.status = models.PurchaseOrderStatus.SENT_TO_VENDOR
                db.add(po)
                await db.commit()
                await db.refresh(po)
                return True
        except Exception as exc:
            logger.warning("erp_send_failed", po_id=po.id, error=str(exc))
        await notification_service.send_po_created(po)
        return False

    async def _calculate_quantity(self, db: AsyncSession, product: models.Product) -> int:
        events = await event_crud.get_for_product(db, product.id, limit=100)
        if len(events) < 2:
            return product.reorder_quantity
        deltas = []
        for previous, current in zip(events[1:], events[:-1]):
            deltas.append(max(0.0, float(previous.fullness_after) - float(current.fullness_after)))
        daily_consumption_rate = (sum(deltas) / max(1, len(deltas))) * product.max_capacity
        adjustment = int(daily_consumption_rate * 1.2)
        quantity = product.reorder_quantity + adjustment
        return max(1, min(quantity, product.max_capacity - product.current_stock))


reorder_service = ReorderService()
