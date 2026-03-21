from __future__ import annotations

from typing import Any


class AnomalyDetector:
    async def analyze(self, image: Any) -> list[str]:
        return []


anomaly_detector = AnomalyDetector()
