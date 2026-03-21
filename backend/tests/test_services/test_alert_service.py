from __future__ import annotations

import numpy as np

from app.db import models
from app.services.alert_service import alert_service
from app.vision.types import DetectionResult, MotionEvent, ZoneAnalysis


async def test_stock_empty_creates_critical_alert(async_db, seeded_product):
    result = DetectionResult(
        camera_id=seeded_product.camera_id,
        zones={
            seeded_product.zone_id: ZoneAnalysis(
                zone_id=seeded_product.zone_id,
                fullness_score=0.05,
                status="empty",
                confidence=0.97,
                bbox=(0, 0, 10, 10)
            )
        },
        global_stats={"avg_fullness": 0.05},
        persons_detected=0,
        motion_events=[],
        processing_time_ms=20,
        stage_used="heuristic"
    )
    alerts = await alert_service.process_detection(async_db, result)
    assert alerts
    assert alerts[0].severity == models.Severity.CRITICAL


async def test_duplicate_alert_deduplication(async_db, seeded_product):
    result = DetectionResult(
        camera_id=seeded_product.camera_id,
        zones={seeded_product.zone_id: ZoneAnalysis(zone_id=seeded_product.zone_id, fullness_score=0.1, status="critical", confidence=0.9, bbox=(0, 0, 10, 10))},
        global_stats={},
        persons_detected=0,
        motion_events=[],
        processing_time_ms=20,
        stage_used="heuristic"
    )
    first = await alert_service.process_detection(async_db, result)
    second = await alert_service.process_detection(async_db, result)
    assert len(first) == 1
    assert len(second) == 0


async def test_auto_resolve_on_restock(async_db, seeded_product):
    result = DetectionResult(
        camera_id=seeded_product.camera_id,
        zones={seeded_product.zone_id: ZoneAnalysis(zone_id=seeded_product.zone_id, fullness_score=0.1, status="critical", confidence=0.9, bbox=(0, 0, 10, 10))},
        global_stats={},
        persons_detected=0,
        motion_events=[],
        processing_time_ms=20,
        stage_used="heuristic"
    )
    await alert_service.process_detection(async_db, result)
    resolved = await alert_service.auto_resolve_check(async_db, seeded_product.zone_id, seeded_product.camera_id, 0.8)
    assert resolved
    assert resolved[0].status == models.AlertStatus.AUTO_RESOLVED


async def test_alert_rate_limiting(async_db, seeded_product):
    result = DetectionResult(
        camera_id=seeded_product.camera_id,
        zones={seeded_product.zone_id: ZoneAnalysis(zone_id=seeded_product.zone_id, fullness_score=0.1, status="critical", confidence=0.9, bbox=(0, 0, 10, 10))},
        global_stats={},
        persons_detected=0,
        motion_events=[],
        processing_time_ms=20,
        stage_used="heuristic"
    )
    first = await alert_service.process_detection(async_db, result)
    second = await alert_service.process_detection(async_db, result)
    assert len(first) == 1
    assert second == []
