from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import models
from app.db.schemas import (
    AlertCreate,
    AlertUpdate,
    CameraCreate,
    CameraUpdate,
    DetectionEventCreate,
    DetectionEventUpdate,
    ProductCreate,
    ProductUpdate,
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    SystemSettingCreate,
    SystemSettingUpdate,
    UserCreate,
    UserUpdate,
    VendorCreate,
    VendorUpdate,
)


ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, item_id: Any) -> ModelType | None:
        return await db.get(self.model, item_id)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        options: Sequence[Any] | None = None,
    ) -> list[ModelType]:
        query = select(self.model)
        if options:
            for option in options:
                query = query.options(option)
        if filters:
            query = self._apply_filters(query, filters)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count(self, db: AsyncSession, *, filters: dict[str, Any] | None = None) -> int:
        query = select(func.count()).select_from(self.model)
        if filters:
            query = self._apply_filters(query, filters)
        result = await db.execute(query)
        return int(result.scalar_one())

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType | dict[str, Any]) -> ModelType:
        data = obj_in.model_dump(exclude_unset=True, exclude_none=True) if isinstance(obj_in, BaseModel) else obj_in
        db_obj = self.model(**data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        data = obj_in.model_dump(exclude_unset=True, exclude_none=True) if isinstance(obj_in, BaseModel) else obj_in
        for field, value in data.items():
            setattr(db_obj, field, value)
        if hasattr(db_obj, "updated_at"):
            setattr(db_obj, "updated_at", datetime.utcnow())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, item_id: Any) -> bool:
        db_obj = await self.get(db, item_id)
        if not db_obj:
            return False
        await db.delete(db_obj)
        await db.commit()
        return True

    async def search(self, db: AsyncSession, *, query: str, fields: list[str], limit: int = 25) -> list[ModelType]:
        return await self.search_with_options(db, query=query, fields=fields, limit=limit)

    async def search_with_options(
        self,
        db: AsyncSession,
        *,
        query: str,
        fields: list[str],
        limit: int = 25,
        options: Sequence[Any] | None = None,
    ) -> list[ModelType]:
        clauses = [cast(getattr(self.model, field), String).ilike(f"%{query}%") for field in fields]
        statement = select(self.model)
        if options:
            for option in options:
                statement = statement.options(option)
        statement = statement.where(or_(*clauses)).limit(limit)
        result = await db.execute(statement)
        return list(result.scalars().all())

    def _apply_filters(self, query: Any, filters: dict[str, Any]) -> Any:
        conditions = []
        for field, value in filters.items():
            if value is None or not hasattr(self.model, field):
                continue
            column = getattr(self.model, field)
            if isinstance(value, list):
                conditions.append(column.in_(value))
            else:
                conditions.append(column == value)
        if conditions:
            query = query.where(and_(*conditions))
        return query


class CRUDVendor(CRUDBase[models.Vendor, VendorCreate, VendorUpdate]):
    async def get_by_name(self, db: AsyncSession, name: str) -> models.Vendor | None:
        statement = select(models.Vendor).where(models.Vendor.name == name)
        result = await db.execute(statement)
        return result.scalars().first()


class CRUDCamera(CRUDBase[models.Camera, CameraCreate, CameraUpdate]):
    async def get_by_zone(self, db: AsyncSession, *, zone: str) -> list[models.Camera]:
        return await self.get_multi(db, filters={"zone": zone})


class CRUDProduct(CRUDBase[models.Product, ProductCreate, ProductUpdate]):
    async def get_by_sku(self, db: AsyncSession, *, sku: str) -> models.Product | None:
        statement = (
            select(models.Product)
            .options(
                selectinload(models.Product.vendor),
                selectinload(models.Product.alerts).selectinload(models.Alert.event),
                selectinload(models.Product.events),
            )
            .where(models.Product.sku == sku)
        )
        result = await db.execute(statement)
        return result.scalars().first()

    async def update_stock(self, db: AsyncSession, product_id: str, new_stock_count: int) -> models.Product:
        product = await self.get(db, product_id)
        if not product:
            raise ValueError(f"Product not found: {product_id}")
        product.current_stock = max(0, new_stock_count)
        product.updated_at = datetime.utcnow()
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    async def get_below_threshold(self, db: AsyncSession) -> list[models.Product]:
        statement = select(models.Product).options(selectinload(models.Product.vendor)).where(models.Product.current_stock <= models.Product.reorder_threshold)
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def get_by_zone(self, db: AsyncSession, zone_id: str) -> list[models.Product]:
        return await self.get_multi(db, filters={"zone_id": zone_id}, options=[selectinload(models.Product.vendor)])


class CRUDDetectionEvent(CRUDBase[models.DetectionEvent, DetectionEventCreate, DetectionEventUpdate]):
    async def get_recent(self, db: AsyncSession, minutes: int = 60) -> list[models.DetectionEvent]:
        threshold = datetime.utcnow() - timedelta(minutes=minutes)
        statement = (
            select(models.DetectionEvent)
            .options(selectinload(models.DetectionEvent.product), selectinload(models.DetectionEvent.camera))
            .where(models.DetectionEvent.created_at >= threshold)
            .order_by(models.DetectionEvent.created_at.desc())
        )
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def get_analytics(self, db: AsyncSession, date_from: date, date_to: date) -> dict[str, Any]:
        start = datetime.combine(date_from, datetime.min.time())
        end = datetime.combine(date_to, datetime.max.time())
        statement = (
            select(
                models.DetectionEvent.event_type,
                models.DetectionEvent.severity,
                func.count().label("total"),
            )
            .where(models.DetectionEvent.created_at.between(start, end))
            .group_by(models.DetectionEvent.event_type, models.DetectionEvent.severity)
        )
        result = await db.execute(statement)
        rows = result.all()
        by_type: dict[str, dict[str, int]] = {}
        for event_type, severity, total in rows:
            by_type.setdefault(event_type.value, {})[severity.value] = int(total)
        return {"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "by_type": by_type}

    async def get_for_product(self, db: AsyncSession, product_id: str, limit: int = 50) -> list[models.DetectionEvent]:
        statement = (
            select(models.DetectionEvent)
            .where(models.DetectionEvent.product_id == product_id)
            .order_by(models.DetectionEvent.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(statement)
        return list(result.scalars().all())


class CRUDAlert(CRUDBase[models.Alert, AlertCreate, AlertUpdate]):
    async def get_active(self, db: AsyncSession) -> list[models.Alert]:
        statement = (
            select(models.Alert)
            .options(selectinload(models.Alert.product), selectinload(models.Alert.event))
            .where(models.Alert.status.in_([models.AlertStatus.ACTIVE, models.AlertStatus.ACKNOWLEDGED]))
            .order_by(models.Alert.created_at.desc())
        )
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def acknowledge(self, db: AsyncSession, alert_id: str, user: str) -> models.Alert | None:
        alert = await self.get(db, alert_id)
        if not alert:
            return None
        if alert.status == models.AlertStatus.RESOLVED:
            return alert
        alert.status = models.AlertStatus.ACKNOWLEDGED
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return alert


class CRUDPurchaseOrder(CRUDBase[models.PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate]):
    async def generate_from_alert(self, db: AsyncSession, alert_id: str) -> models.PurchaseOrder:
        alert = await db.get(models.Alert, alert_id)
        if not alert or not alert.product_id:
            raise ValueError("Alert not eligible for PO generation.")
        product = await db.get(models.Product, alert.product_id)
        if not product:
            raise ValueError("Product not found for alert.")
        next_id = await self._next_po_id(db)
        unit_cost = Decimal(product.unit_cost)
        total_amount = unit_cost * product.reorder_quantity
        po = models.PurchaseOrder(
            id=next_id,
            product_id=product.id,
            vendor_id=product.vendor_id,
            trigger_alert_id=alert.id,
            quantity_ordered=product.reorder_quantity,
            unit_cost=unit_cost,
            total_amount=total_amount,
            status=models.PurchaseOrderStatus.PENDING_APPROVAL,
        )
        db.add(po)
        await db.commit()
        await db.refresh(po)
        return po

    async def approve(self, db: AsyncSession, po_id: str, approved_by: str) -> models.PurchaseOrder | None:
        po = await self.get(db, po_id)
        if not po:
            return None
        po.status = models.PurchaseOrderStatus.APPROVED
        po.approved_by = approved_by
        po.approved_at = datetime.utcnow()
        db.add(po)
        await db.commit()
        await db.refresh(po)
        return po

    async def get_pending_by_product(self, db: AsyncSession, product_id: str) -> models.PurchaseOrder | None:
        statement = select(models.PurchaseOrder).where(
            models.PurchaseOrder.product_id == product_id,
            models.PurchaseOrder.status.in_(
                [
                    models.PurchaseOrderStatus.DRAFT,
                    models.PurchaseOrderStatus.PENDING_APPROVAL,
                    models.PurchaseOrderStatus.APPROVED,
                    models.PurchaseOrderStatus.SENT_TO_VENDOR,
                    models.PurchaseOrderStatus.CONFIRMED,
                ]
            ),
        )
        result = await db.execute(statement)
        return result.scalars().first()

    async def _next_po_id(self, db: AsyncSession) -> str:
        current_year = datetime.utcnow().year
        prefix = f"PO-{current_year}-"
        statement = select(models.PurchaseOrder.id).where(models.PurchaseOrder.id.like(f"{prefix}%")).order_by(models.PurchaseOrder.id.desc())
        result = await db.execute(statement)
        last_id = result.scalars().first()
        if not last_id:
            return f"{prefix}0001"
        next_num = int(last_id.split("-")[-1]) + 1
        return f"{prefix}{next_num:04d}"


class CRUDUser(CRUDBase[models.User, UserCreate, UserUpdate]):
    async def get_by_username(self, db: AsyncSession, username: str) -> models.User | None:
        statement = select(models.User).where(models.User.username == username)
        result = await db.execute(statement)
        return result.scalars().first()

    async def get_by_email(self, db: AsyncSession, email: str) -> models.User | None:
        statement = select(models.User).where(models.User.email == email)
        result = await db.execute(statement)
        return result.scalars().first()


class CRUDSystemSettings(CRUDBase[models.SystemSettings, SystemSettingCreate, SystemSettingUpdate]):
    async def get_dict(self, db: AsyncSession) -> dict[str, Any]:
        items = await self.get_multi(db, limit=500)
        return {item.key: item.value for item in items}


vendor_crud = CRUDVendor(models.Vendor)
camera_crud = CRUDCamera(models.Camera)
product_crud = CRUDProduct(models.Product)
event_crud = CRUDDetectionEvent(models.DetectionEvent)
alert_crud = CRUDAlert(models.Alert)
po_crud = CRUDPurchaseOrder(models.PurchaseOrder)
user_crud = CRUDUser(models.User)
settings_crud = CRUDSystemSettings(models.SystemSettings)
