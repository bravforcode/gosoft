from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models


async def test_get_inventory_authenticated(test_client, auth_headers, seeded_product):
    response = await test_client.get("/api/v1/inventory", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"][0]["sku"] == seeded_product.sku


async def test_get_inventory_unauthenticated(test_client, seeded_product):
    response = await test_client.get("/api/v1/inventory")
    assert response.status_code == 401


async def test_get_inventory_pagination(test_client, auth_headers, async_db: AsyncSession, seeded_vendor, seeded_camera):
    for index in range(5):
        async_db.add(
            models.Product(
                sku=f"SKU-{index + 10}",
                name_th=f"สินค้า {index}",
                name_en=f"Product {index}",
                brand="Brand",
                category="Category",
                zone_id="A-01",
                camera_id=seeded_camera.id,
                max_capacity=20,
                current_stock=10,
                reorder_threshold=5,
                reorder_quantity=10,
                unit_cost=10,
                unit_price=15,
                vendor_id=seeded_vendor.id,
                shelf_position={"row": 1, "col": index},
                product_color_hex="#fff",
            )
        )
    await async_db.commit()
    response = await test_client.get("/api/v1/inventory?skip=1&limit=2", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["pagination"]["limit"] == 2


async def test_get_product_by_sku(test_client, auth_headers, seeded_product):
    response = await test_client.get(f"/api/v1/inventory/{seeded_product.sku}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["sku"] == seeded_product.sku


async def test_get_nonexistent_sku(test_client, auth_headers):
    response = await test_client.get("/api/v1/inventory/NOPE", headers=auth_headers)
    assert response.status_code == 404


async def test_get_critical_products(test_client, auth_headers, seeded_product):
    response = await test_client.get("/api/v1/inventory/critical", headers=auth_headers)
    assert response.status_code == 200
    assert any(item["sku"] == seeded_product.sku for item in response.json())


async def test_update_product_admin(test_client, auth_headers, seeded_product):
    response = await test_client.put(
        f"/api/v1/inventory/{seeded_product.sku}",
        headers=auth_headers,
        json={"reorder_threshold": 6},
    )
    assert response.status_code == 200
    assert response.json()["reorder_threshold"] == 6


async def test_update_product_viewer(test_client, viewer_headers, seeded_product):
    response = await test_client.put(
        f"/api/v1/inventory/{seeded_product.sku}",
        headers=viewer_headers,
        json={"reorder_threshold": 6},
    )
    assert response.status_code == 403
