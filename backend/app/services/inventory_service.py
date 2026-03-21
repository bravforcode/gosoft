from __future__ import annotations

import csv
import io
import json
from typing import Any

from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.crud import event_crud, product_crud, vendor_crud
from app.db.schemas import AlertRead, DetectionEventRead, ImportResult, ProductCreate, ProductDetail, ProductSummary, ProductUpdate, StockHistoryPoint


class InventoryService:
    async def list_products(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        zone: str | None = None,
        category: str | None = None,
    ) -> tuple[list[models.Product], int]:
        filters: dict[str, Any] = {}
        if zone:
            filters["zone_id"] = zone
        if category:
            filters["category"] = category
        if search:
            products = await product_crud.search_with_options(
                db,
                query=search,
                fields=["sku", "name_en", "name_th", "brand"],
                limit=limit,
                options=[selectinload(models.Product.vendor)],
            )
            return products, len(products)
        total = await product_crud.count(db, filters=filters or None)
        products = await product_crud.get_multi(
            db,
            skip=skip,
            limit=limit,
            filters=filters or None,
            options=[selectinload(models.Product.vendor)],
        )
        return products, total

    async def get_product_detail(self, db: AsyncSession, sku: str) -> ProductDetail | None:
        product = await product_crud.get_by_sku(db, sku=sku)
        if not product:
            return None
        history_events = await event_crud.get_for_product(db, product.id)
        history = [
            StockHistoryPoint(
                timestamp=event.created_at,
                current_stock=product.current_stock if index == 0 else max(0, int(product.max_capacity * float(event.fullness_after))),
                fullness_after=float(event.fullness_after),
            )
            for index, event in enumerate(reversed(history_events))
        ]
        return ProductDetail.model_validate(
            {
                **ProductSummary.model_validate(product).model_dump(),
                "alerts": [AlertRead.model_validate(alert_item) for alert_item in product.alerts],
                "events": [DetectionEventRead.model_validate(event_item) for event_item in history_events],
                "stock_history": history,
            }
        )

    async def update_product(self, db: AsyncSession, sku: str, payload: ProductUpdate) -> models.Product | None:
        product = await product_crud.get_by_sku(db, sku=sku)
        if not product:
            return None
        return await product_crud.update(db, db_obj=product, obj_in=payload)

    async def get_history(self, db: AsyncSession, sku: str) -> list[StockHistoryPoint]:
        product = await product_crud.get_by_sku(db, sku=sku)
        if not product:
            return []
        events = await event_crud.get_for_product(db, product.id)
        history = []
        for event in reversed(events):
            history.append(
                StockHistoryPoint(
                    timestamp=event.created_at,
                    current_stock=max(0, int(product.max_capacity * float(event.fullness_after))),
                    fullness_after=float(event.fullness_after),
                )
            )
        return history

    async def import_csv(self, db: AsyncSession, content: bytes) -> ImportResult:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        imported = 0
        skipped = 0
        errors: list[str] = []
        for row in reader:
            try:
                vendor_name = row.get("vendor_name") or row.get("vendor")
                if not vendor_name:
                    raise ValueError("vendor missing")
                vendor = await vendor_crud.get_by_name(db, vendor_name) if hasattr(vendor_crud, "get_by_name") else None
                if not vendor:
                    vendor = await vendor_crud.create(
                        db,
                        obj_in={
                            "name": vendor_name,
                            "lead_time_days": int(row.get("lead_time_days") or 1),
                        },
                    )
                existing = await product_crud.get_by_sku(db, sku=row["sku"])
                payload = ProductCreate(
                    sku=row["sku"],
                    name_th=row["name_th"],
                    name_en=row["name_en"],
                    brand=row["brand"],
                    category=row["category"],
                    barcode=row.get("barcode"),
                    zone_id=row["zone_id"],
                    camera_id=row["camera_id"],
                    max_capacity=int(row["max_capacity"]),
                    current_stock=int(row.get("current_stock") or 0),
                    reorder_threshold=int(row["reorder_threshold"]),
                    reorder_quantity=int(row["reorder_quantity"]),
                    unit_cost=row["unit_cost"],
                    unit_price=row["unit_price"],
                    vendor_id=vendor.id,
                    shelf_position=json.loads(row.get("shelf_position") or "{}"),
                    product_color_hex=row["product_color_hex"],
                    image_url=row.get("image_url"),
                    is_active=(row.get("is_active", "true").lower() != "false"),
                )
                if existing:
                    await product_crud.update(db, db_obj=existing, obj_in=payload.model_dump(exclude={"sku"}))
                    skipped += 1
                else:
                    await product_crud.create(db, obj_in=payload)
                    imported += 1
            except Exception as exc:
                errors.append(f"{row.get('sku', 'unknown')}: {exc}")
        return ImportResult(imported=imported, skipped=skipped, errors=errors)

    async def export_csv(self, db: AsyncSession) -> str:
        products = await product_crud.get_multi(db, limit=1000)
        output = io.StringIO()
        fieldnames = [
            "sku",
            "name_th",
            "name_en",
            "brand",
            "category",
            "barcode",
            "zone_id",
            "camera_id",
            "max_capacity",
            "current_stock",
            "reorder_threshold",
            "reorder_quantity",
            "unit_cost",
            "unit_price",
            "vendor_id",
            "shelf_position",
            "product_color_hex",
            "image_url",
            "is_active",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for product in products:
            writer.writerow(
                {
                    "sku": product.sku,
                    "name_th": product.name_th,
                    "name_en": product.name_en,
                    "brand": product.brand,
                    "category": product.category,
                    "barcode": product.barcode,
                    "zone_id": product.zone_id,
                    "camera_id": product.camera_id,
                    "max_capacity": product.max_capacity,
                    "current_stock": product.current_stock,
                    "reorder_threshold": product.reorder_threshold,
                    "reorder_quantity": product.reorder_quantity,
                    "unit_cost": str(product.unit_cost),
                    "unit_price": str(product.unit_price),
                    "vendor_id": product.vendor_id,
                    "shelf_position": json.dumps(product.shelf_position),
                    "product_color_hex": product.product_color_hex,
                    "image_url": product.image_url,
                    "is_active": product.is_active,
                }
            )
        return output.getvalue()

    async def get_critical_products(self, db: AsyncSession) -> list[models.Product]:
        return await product_crud.get_below_threshold(db)


inventory_service = InventoryService()
