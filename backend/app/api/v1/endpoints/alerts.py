from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.exceptions import error_response
from app.db import models
from app.db.crud import alert_crud
from app.db.database import get_db
from app.db.models import User, UserRole
from app.db.schemas import AlertDetail, AlertRead, AlertUpdate, BulkResult, PaginatedAlertList


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=PaginatedAlertList)
async def get_alerts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    zone: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedAlertList:
    statement = (
        select(models.Alert)
        .options(selectinload(models.Alert.event), selectinload(models.Alert.product))
        .join(models.DetectionEvent)
    )
    if status_filter:
        statement = statement.where(models.Alert.status == status_filter)
    if severity:
        statement = statement.where(models.Alert.severity == severity)
    if zone:
        statement = statement.where(models.DetectionEvent.zone == zone)
    total = len((await db.execute(statement)).scalars().all())
    result = await db.execute(statement.offset(skip).limit(limit))
    items = [AlertRead.model_validate(item) for item in result.scalars().all()]
    return PaginatedAlertList(items=items, pagination={"total": total, "skip": skip, "limit": limit})


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> AlertDetail:
    statement = select(models.Alert).options(selectinload(models.Alert.event), selectinload(models.Alert.product)).where(models.Alert.id == alert_id)
    alert = (await db.execute(statement)).scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail=error_response("alert_not_found", "Alert not found.", {"alert_id": alert_id}))
    return AlertDetail.model_validate(
        {
            **alert.__dict__,
            "evidence_frame_url": f"/api/v1/alerts/{alert.id}/evidence" if alert.evidence_frame_path else None,
        }
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertDetail)
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> AlertDetail:
    alert = await alert_crud.acknowledge(db, alert_id, current_user.username)
    if not alert:
        raise HTTPException(status_code=404, detail=error_response("alert_not_found", "Alert not found.", {"alert_id": alert_id}))
    return await get_alert(alert_id, db)


@router.post("/{alert_id}/resolve", response_model=AlertDetail)
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> AlertDetail:
    alert = await alert_crud.get(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=error_response("alert_not_found", "Alert not found.", {"alert_id": alert_id}))
    await alert_crud.update(
        db,
        db_obj=alert,
        obj_in=AlertUpdate(status=models.AlertStatus.RESOLVED, resolved_by=current_user.username),
    )
    return await get_alert(alert_id, db)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> None:
    deleted = await alert_crud.delete(db, item_id=alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=error_response("alert_not_found", "Alert not found.", {"alert_id": alert_id}))


@router.post("/bulk-acknowledge", response_model=BulkResult)
async def bulk_acknowledge_alerts(
    alert_ids: list[str],
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> BulkResult:
    succeeded = 0
    failed = 0
    ids: list[str] = []
    for alert_id in alert_ids:
        alert = await alert_crud.acknowledge(db, alert_id, current_user.username)
        if alert:
            succeeded += 1
            ids.append(alert.id)
        else:
            failed += 1
    return BulkResult(processed=len(alert_ids), succeeded=succeeded, failed=failed, ids=ids)


@router.get("/{alert_id}/evidence")
async def get_alert_evidence(alert_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    alert = await alert_crud.get(db, alert_id)
    if not alert or not alert.evidence_frame_path:
        raise HTTPException(status_code=404, detail=error_response("evidence_not_found", "Evidence not found.", {"alert_id": alert_id}))
    path = Path(alert.evidence_frame_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=error_response("evidence_not_found", "Evidence not found on disk.", {"alert_id": alert_id}))
    return FileResponse(path)
