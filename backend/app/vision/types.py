from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Frame:
    camera_id: str
    data: Any
    timestamp: datetime
    frame_number: int
    width: int
    height: int


@dataclass
class ZoneAnalysis:
    zone_id: str
    fullness_score: float
    status: str
    products_detected: list[str] = field(default_factory=list)
    product_count: int = 0
    confidence: float = 0.0
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    anomalies: list[str] = field(default_factory=list)
    ai_verified: bool = False


@dataclass
class MotionEvent:
    zone_id: str
    movement_score: float
    detected_at: datetime


@dataclass
class DetectionResult:
    camera_id: str
    zones: dict[str, ZoneAnalysis]
    global_stats: dict[str, Any]
    persons_detected: int
    motion_events: list[MotionEvent]
    processing_time_ms: float
    stage_used: str
    raw_detections: list[dict[str, Any]] = field(default_factory=list)
