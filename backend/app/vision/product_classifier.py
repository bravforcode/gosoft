from __future__ import annotations

from typing import Any


class ProductClassifier:
    async def classify(self, image: Any) -> dict[str, float]:
        return {}


product_classifier = ProductClassifier()
