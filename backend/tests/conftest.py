from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["API_KEY"] = "test-api-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_siv.db"
os.environ["REDIS_URL"] = "redis://localhost:6399/15"
os.environ["DEBUG"] = "false"
os.environ["CAMERA_0_URL"] = ""
os.environ["CAMERA_1_URL"] = ""
os.environ["CAMERA_2_URL"] = ""
os.environ["CAMERA_3_URL"] = ""

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash
from app.db import models
from app.db.database import init_db
from app.main import app


settings = get_settings()
test_engine = create_async_engine(settings.DATABASE_URL, future=True)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def prepare_db() -> AsyncIterator[None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)
    yield


@pytest.fixture
async def async_db() -> AsyncIterator[AsyncSession]:
    async with TestSessionLocal() as session:
        for table in [
            models.PurchaseOrder,
            models.Alert,
            models.DetectionEvent,
            models.Product,
            models.Camera,
            models.Vendor,
            models.User,
            models.SystemSettings,
        ]:
            await session.execute(delete(table))
        await session.commit()
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def override_db() -> AsyncIterator[None]:
    async def _override() -> AsyncIterator[AsyncSession]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def test_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def admin_user(async_db: AsyncSession) -> models.User:
    user = models.User(
        username="admin-test",
        email="admin-test@siv.local",
        hashed_password=get_password_hash("admin123"),
        role=models.UserRole.ADMIN,
        is_active=True,
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest.fixture
async def viewer_user(async_db: AsyncSession) -> models.User:
    user = models.User(
        username="viewer-test",
        email="viewer-test@siv.local",
        hashed_password=get_password_hash("viewer123"),
        role=models.UserRole.VIEWER,
        is_active=True,
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest.fixture
async def seeded_vendor(async_db: AsyncSession) -> models.Vendor:
    vendor = models.Vendor(name="Vendor Test", lead_time_days=1)
    async_db.add(vendor)
    await async_db.commit()
    await async_db.refresh(vendor)
    return vendor


@pytest.fixture
async def seeded_camera(async_db: AsyncSession) -> models.Camera:
    camera = models.Camera(
        id="CAM-01",
        name="Camera 1",
        zone="Zone A",
        stream_url="0",
        status=models.CameraStatus.ONLINE,
        resolution_width=1280,
        resolution_height=720,
        fps_processing=2.0,
    )
    async_db.add(camera)
    await async_db.commit()
    await async_db.refresh(camera)
    return camera


@pytest.fixture
async def seeded_product(async_db: AsyncSession, seeded_vendor: models.Vendor, seeded_camera: models.Camera) -> models.Product:
    product = models.Product(
        sku="SKU-001",
        name_th="สินค้า",
        name_en="Product One",
        brand="Brand",
        category="Category",
        zone_id="A-01",
        camera_id=seeded_camera.id,
        max_capacity=20,
        current_stock=5,
        reorder_threshold=8,
        reorder_quantity=12,
        unit_cost=10,
        unit_price=15,
        vendor_id=seeded_vendor.id,
        shelf_position={"row": 1, "col": 1},
        product_color_hex="#ffffff",
    )
    async_db.add(product)
    await async_db.commit()
    await async_db.refresh(product)
    return product


@pytest.fixture
async def auth_headers(admin_user: models.User) -> dict[str, str]:
    token = create_access_token(admin_user.id, {"role": admin_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def viewer_headers(viewer_user: models.User) -> dict[str, str]:
    token = create_access_token(viewer_user.id, {"role": viewer_user.role.value})
    return {"Authorization": f"Bearer {token}"}
