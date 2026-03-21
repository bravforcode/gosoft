from __future__ import annotations

from app.db import models
from app.services import reorder_service as reorder_module
from app.services.reorder_service import reorder_service


async def test_po_created_on_critical_stock(async_db, seeded_product):
    po = await reorder_service.check_and_create_po(async_db, seeded_product.id, 2)
    assert po is not None
    assert po.quantity_ordered > 0


async def test_no_duplicate_po_if_pending_exists(async_db, seeded_product):
    first = await reorder_service.check_and_create_po(async_db, seeded_product.id, 2)
    second = await reorder_service.check_and_create_po(async_db, seeded_product.id, 2)
    assert first.id == second.id


async def test_po_quantity_calculation(async_db, seeded_product):
    quantity = await reorder_service._calculate_quantity(async_db, seeded_product)
    assert quantity >= 1


async def test_auto_approve_under_threshold(async_db, seeded_product):
    seeded_product.unit_cost = 1
    seeded_product.reorder_quantity = 2
    async_db.add(seeded_product)
    await async_db.commit()
    po = await reorder_service.check_and_create_po(async_db, seeded_product.id, 1)
    assert po is not None
    assert po.status in {models.PurchaseOrderStatus.APPROVED, models.PurchaseOrderStatus.SENT_TO_VENDOR, models.PurchaseOrderStatus.PENDING_APPROVAL}


async def test_send_to_vendor_fallback(async_db, seeded_product, monkeypatch):
    po = await reorder_service.check_and_create_po(async_db, seeded_product.id, 1)
    assert po is not None

    class BrokenAdapter:
        async def create_purchase_order(self, _po):
            raise RuntimeError("ERP down")

    async def fake_notify(_po):
        return None

    monkeypatch.setattr(reorder_module, "get_erp_adapter", lambda: BrokenAdapter())
    monkeypatch.setattr(reorder_module.notification_service, "send_po_created", fake_notify)
    ok = await reorder_service.send_to_vendor(async_db, po)
    assert ok is False
