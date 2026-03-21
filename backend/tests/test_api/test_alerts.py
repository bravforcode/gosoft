from __future__ import annotations

from app.db import models


async def create_alert(async_db, seeded_product):
    event = models.DetectionEvent(
        camera_id=seeded_product.camera_id,
        product_id=seeded_product.id,
        zone=seeded_product.zone_id,
        event_type=models.EventType.EMPTY_SHELF,
        severity=models.Severity.CRITICAL,
        fullness_before=0.2,
        fullness_after=0.05,
        confidence=0.98,
    )
    async_db.add(event)
    await async_db.commit()
    await async_db.refresh(event)
    alert = models.Alert(
        event_id=event.id,
        product_id=seeded_product.id,
        camera_id=seeded_product.camera_id,
        title="Alert",
        description="Desc",
        severity=models.Severity.CRITICAL,
        status=models.AlertStatus.ACTIVE,
    )
    async_db.add(alert)
    await async_db.commit()
    await async_db.refresh(alert)
    return alert


async def test_get_alerts_filters(test_client, auth_headers, async_db, seeded_product):
    await create_alert(async_db, seeded_product)
    response = await test_client.get("/api/v1/alerts?status=active&severity=critical", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["pagination"]["total"] >= 1


async def test_acknowledge_alert(test_client, auth_headers, async_db, seeded_product):
    alert = await create_alert(async_db, seeded_product)
    response = await test_client.post(f"/api/v1/alerts/{alert.id}/acknowledge", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"


async def test_acknowledge_alert_twice(test_client, auth_headers, async_db, seeded_product):
    alert = await create_alert(async_db, seeded_product)
    await test_client.post(f"/api/v1/alerts/{alert.id}/acknowledge", headers=auth_headers)
    response = await test_client.post(f"/api/v1/alerts/{alert.id}/acknowledge", headers=auth_headers)
    assert response.status_code == 200


async def test_resolve_alert(test_client, auth_headers, async_db, seeded_product):
    alert = await create_alert(async_db, seeded_product)
    response = await test_client.post(f"/api/v1/alerts/{alert.id}/resolve", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
