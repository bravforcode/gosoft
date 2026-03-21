from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any

import cv2
from anthropic import AsyncAnthropic

from app.cache.cache_service import cache_service
from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger("vision.claude")


@dataclass
class ZoneImage:
    camera_id: str
    zone_id: str
    image: Any


@dataclass
class ClaudeZoneResult:
    zone_id: str
    products: list[dict[str, Any]]
    empty_slots: int
    fullness_percent: int
    anomalies: list[str]
    planogram_compliance: float
    notes: str


@dataclass
class PlanogramResult:
    compliance_score: float
    mismatches: list[str]
    notes: str


class ClaudeVisionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = AsyncAnthropic(api_key=self.settings.CLAUDE_API_KEY) if self.settings.CLAUDE_API_KEY else None
        self._semaphore = asyncio.Semaphore(5)

    async def analyze_zones(self, zones: list[ZoneImage]) -> list[ClaudeZoneResult]:
        if not self._client or not self.settings.CLAUDE_VISION_ENABLED or not zones:
            return []
        chunk = zones[:3]
        cache_key = self._cache_key(chunk)
        cached = await cache_service.get_json(cache_key)
        if cached:
            return [ClaudeZoneResult(**item) for item in cached]
        async with self._semaphore:
            try:
                message_content: list[dict[str, Any]] = []
                for zone in chunk:
                    message_content.append({"type": "text", "text": f"Zone {zone.zone_id}:"})
                    message_content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": self._encode_image(zone.image),
                            },
                        }
                    )
                response = await self._client.messages.create(
                    model=self.settings.CLAUDE_MODEL,
                    max_tokens=800,
                    system="You are a retail inventory AI. Respond only with valid JSON.",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Analyze these shelf zones and return a JSON array."},
                                *message_content,
                            ],
                        }
                    ],
                )
                text = "".join(block.text for block in response.content if hasattr(block, "text"))
                payload = json.loads(text)
                results = [ClaudeZoneResult(**item) for item in payload]
                await cache_service.set_json(cache_key, [result.__dict__ for result in results], ttl=self.settings.CLAUDE_CACHE_SECONDS)
                logger.info("claude_analysis_complete", zones=[zone.zone_id for zone in chunk])
                return results
            except Exception as exc:
                logger.warning("claude_analysis_failed", error=str(exc))
                return []

    async def detect_planogram_violation(self, frame: Any, expected_layout: dict) -> PlanogramResult:
        if not self._client:
            return PlanogramResult(compliance_score=1.0, mismatches=[], notes="Claude disabled.")
        return PlanogramResult(compliance_score=0.84, mismatches=[], notes="Reference comparison unavailable in local mode.")

    def _encode_image(self, image: Any) -> str:
        resized = cv2.resize(image, (512, 512), interpolation=cv2.INTER_AREA)
        success, buffer = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode image.")
        return base64.b64encode(buffer.tobytes()).decode("utf-8")

    def _cache_key(self, zones: list[ZoneImage]) -> str:
        parts = []
        for zone in zones:
            success, buffer = cv2.imencode(".jpg", zone.image)
            if not success:
                continue
            parts.append(hashlib.sha256(buffer.tobytes()).hexdigest())
        return f"claude:{':'.join(parts)}"


claude_vision_service = ClaudeVisionService()
