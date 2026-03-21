from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.crud import settings_crud
from app.db.database import get_db
from app.db.models import User, UserRole
from app.db.schemas import ConnectionTestResult, DiscoveredCamera, NotificationTestResult, SettingItem, SettingsDict, SystemSettingUpdate
from app.services.erp_service import get_erp_adapter
from app.services.notification_service import notification_service
from app.vision.camera_manager import camera_manager


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsDict)
async def get_settings_items(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> SettingsDict:
    items = await settings_crud.get_multi(db, limit=500)
    return SettingsDict(items=[SettingItem(key=item.key, value=item.value, description=item.description, updated_at=item.updated_at) for item in items])


@router.put("/{key}", response_model=SettingItem)
async def update_setting(
    key: str,
    payload: SystemSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
) -> SettingItem:
    setting = await settings_crud.get(db, key)
    if setting:
        setting = await settings_crud.update(db, db_obj=setting, obj_in={"value": payload.value, "description": payload.description or setting.description, "updated_by": current_user.username})
    else:
        setting = await settings_crud.create(
            db,
            obj_in={
                "key": key,
                "value": payload.value,
                "description": payload.description or key,
                "updated_by": current_user.username,
            },
        )
    return SettingItem(key=setting.key, value=setting.value, description=setting.description, updated_at=setting.updated_at)


@router.get("/cameras/scan", response_model=list[DiscoveredCamera])
async def scan_cameras(_: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))) -> list[DiscoveredCamera]:
    return [
        DiscoveredCamera(id=camera_id, name=camera_id, stream_url=worker.url, zone=f"Auto {index + 1}", vendor="Generic RTSP")
        for index, (camera_id, worker) in enumerate(camera_manager.cameras.items())
    ]


@router.post("/test-erp", response_model=ConnectionTestResult)
async def test_erp(_: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))) -> ConnectionTestResult:
    adapter = get_erp_adapter()
    if not adapter:
        return ConnectionTestResult(ok=False, latency_ms=0.0, message="ERP adapter not configured.")
    products = await adapter.get_product_list()
    return ConnectionTestResult(ok=True, latency_ms=0.0, message="ERP connection ok.", details={"products": len(products)})


@router.post("/test-line", response_model=NotificationTestResult)
async def test_line(_: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))) -> NotificationTestResult:
    await notification_service.send_system_health({"message": "test"})
    return NotificationTestResult(ok=True, channel="line", message="Notification pipeline invoked.")
