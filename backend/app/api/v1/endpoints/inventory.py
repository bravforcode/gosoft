from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.cache.cache_service import cache_service
from app.core.exceptions import error_response
from app.db.database import get_db
from app.db.models import User, UserRole
from app.db.schemas import ImportResult, PaginatedProductList, ProductDetail, ProductSummary, ProductUpdate, StockHistoryPoint
from app.services.inventory_service import inventory_service


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=PaginatedProductList)
async def get_inventory(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    search: str | None = None,
    zone: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedProductList:
    cache_key = f"inventory:{skip}:{limit}:{search}:{zone}:{category}"

    async def producer():
        products, total = await inventory_service.list_products(db, skip=skip, limit=limit, search=search, zone=zone, category=category)
        return {
            "items": [ProductSummary.model_validate(item).model_dump(mode="json") for item in products],
            "pagination": {"total": total, "skip": skip, "limit": limit},
        }

    payload = await cache_service.get_or_set(cache_key, producer)
    return PaginatedProductList.model_validate(payload)


@router.get("/critical", response_model=list[ProductSummary])
async def get_critical_products(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ProductSummary]:
    products = await inventory_service.get_critical_products(db)
    return [ProductSummary.model_validate(product) for product in products]


@router.get("/zone/{zone_id}", response_model=list[ProductSummary])
async def get_inventory_by_zone(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ProductSummary]:
    products, _ = await inventory_service.list_products(db, skip=0, limit=500, zone=zone_id)
    return [ProductSummary.model_validate(product) for product in products]


@router.get("/{sku}", response_model=ProductDetail)
async def get_product_detail(
    sku: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProductDetail:
    product = await inventory_service.get_product_detail(db, sku)
    if not product:
        raise HTTPException(status_code=404, detail=error_response("product_not_found", "Product not found.", {"sku": sku}))
    return product


@router.put("/{sku}", response_model=ProductDetail)
async def update_product(
    sku: str,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> ProductDetail:
    product = await inventory_service.update_product(db, sku, payload)
    if not product:
        raise HTTPException(status_code=404, detail=error_response("product_not_found", "Product not found.", {"sku": sku}))
    detail = await inventory_service.get_product_detail(db, sku)
    if not detail:
        raise HTTPException(status_code=404, detail=error_response("product_not_found", "Product not found.", {"sku": sku}))
    await cache_service.delete(f"inventory:0:50:None:None:None")
    return detail


@router.get("/{sku}/history", response_model=list[StockHistoryPoint])
async def get_product_history(
    sku: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[StockHistoryPoint]:
    history = await inventory_service.get_history(db, sku)
    if not history:
        product = await inventory_service.get_product_detail(db, sku)
        if not product:
            raise HTTPException(status_code=404, detail=error_response("product_not_found", "Product not found.", {"sku": sku}))
    return history


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
async def import_inventory(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> ImportResult:
    content = await file.read()
    return await inventory_service.import_csv(db, content)


@router.get("/export")
async def export_inventory(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    content = await inventory_service.export_csv(db)
    return StreamingResponse(
        BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="inventory.csv"'},
    )
