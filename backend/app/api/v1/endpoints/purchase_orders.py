from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.exceptions import error_response
from app.db import models
from app.db.crud import po_crud
from app.db.database import get_db
from app.db.models import User, UserRole
from app.db.schemas import PODetail, PaginatedPOList, PurchaseOrderCreate, PurchaseOrderRead, PurchaseOrderUpdate
from app.services.reorder_service import reorder_service


router = APIRouter(prefix="/purchase-orders", tags=["purchase_orders"])


def _purchase_order_query():
    return select(models.PurchaseOrder).options(
        selectinload(models.PurchaseOrder.product).selectinload(models.Product.vendor),
        selectinload(models.PurchaseOrder.vendor),
        selectinload(models.PurchaseOrder.trigger_alert),
    )


async def _get_po_or_404(db: AsyncSession, po_id: str) -> models.PurchaseOrder:
    statement = _purchase_order_query().where(models.PurchaseOrder.id == po_id)
    po = (await db.execute(statement)).scalars().first()
    if not po:
        raise HTTPException(status_code=404, detail=error_response("po_not_found", "Purchase order not found.", {"po_id": po_id}))
    return po


@router.get("", response_model=PaginatedPOList)
async def get_purchase_orders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None, alias="status"),
    vendor: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedPOList:
    statement = _purchase_order_query()
    if status_filter:
        statement = statement.where(models.PurchaseOrder.status == status_filter)
    if vendor:
        statement = statement.where(models.PurchaseOrder.vendor_id == vendor)
    total = len((await db.execute(statement)).scalars().all())
    result = await db.execute(statement.offset(skip).limit(limit))
    items = [PurchaseOrderRead.model_validate(item) for item in result.scalars().all()]
    return PaginatedPOList(items=items, pagination={"total": total, "skip": skip, "limit": limit})


@router.get("/{po_id}", response_model=PODetail)
async def get_purchase_order(po_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> PODetail:
    po = await _get_po_or_404(db, po_id)
    return PODetail.model_validate(po)


@router.post("", response_model=PODetail, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> PODetail:
    po_data = payload.model_dump(exclude_none=True)
    if not po_data.get("id"):
        po_data["id"] = await po_crud._next_po_id(db)
    created = await po_crud.create(db, obj_in=po_data)
    po = await _get_po_or_404(db, created.id)
    return PODetail.model_validate(po)


@router.post("/{po_id}/approve", response_model=PODetail)
async def approve_purchase_order(
    po_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> PODetail:
    approved = await reorder_service.approve_and_send(db, po_id, approved_by=current_user.username)
    po = await _get_po_or_404(db, approved.id)
    return PODetail.model_validate(po)


@router.post("/{po_id}/reject", response_model=PODetail)
async def reject_purchase_order(
    po_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> PODetail:
    existing = await _get_po_or_404(db, po_id)
    updated = await po_crud.update(
        db,
        db_obj=existing,
        obj_in=PurchaseOrderUpdate(status=models.PurchaseOrderStatus.CANCELLED, notes=f"Rejected by {current_user.username}"),
    )
    po = await _get_po_or_404(db, updated.id)
    return PODetail.model_validate(po)


@router.post("/{po_id}/send", response_model=PODetail)
async def send_purchase_order(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> PODetail:
    po = await _get_po_or_404(db, po_id)
    await reorder_service.send_to_vendor(db, po)
    refreshed = await _get_po_or_404(db, po_id)
    return PODetail.model_validate(refreshed)


@router.post("/{po_id}/deliver", response_model=PODetail)
async def deliver_purchase_order(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> PODetail:
    existing = await _get_po_or_404(db, po_id)
    updated = await po_crud.update(
        db,
        db_obj=existing,
        obj_in=PurchaseOrderUpdate(status=models.PurchaseOrderStatus.DELIVERED, expected_delivery=datetime.utcnow()),
    )
    po = await _get_po_or_404(db, updated.id)
    return PODetail.model_validate(po)
