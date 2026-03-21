from __future__ import annotations

import numpy as np

from app.vision.shelf_detector import ShelfDetector, YOLODetection


def test_fullness_calculation_bright_zone():
    detector = ShelfDetector()
    image = np.full((120, 120, 3), 220, dtype=np.uint8)
    score = detector._compute_zone_fullness(image, None)
    assert score > 0.5


def test_fullness_calculation_dark_zone():
    detector = ShelfDetector()
    image = np.zeros((120, 120, 3), dtype=np.uint8)
    score = detector._compute_zone_fullness(image, None)
    assert score < 0.2


def test_zone_status_mapping():
    detector = ShelfDetector()
    assert detector._map_status(0.05) == "empty"
    assert detector._map_status(0.2) == "critical"
    assert detector._map_status(0.4) == "low"
    assert detector._map_status(0.8) == "ok"


def test_calibration():
    detector = ShelfDetector()
    image = np.full((120, 120, 3), 200, dtype=np.uint8)
    detector.calibrate("CAM-01", image)
    assert "CAM-01" in detector.calibration_baselines


def test_yolo_detection_mock(monkeypatch):
    detector = ShelfDetector()
    image = np.full((120, 120, 3), 200, dtype=np.uint8)

    monkeypatch.setattr(
        detector,
        "_detect_yolo",
        lambda _: [YOLODetection(class_id=39, confidence=0.92, bbox=(0, 0, 10, 10), label="bottle")],
    )
    detector.frame_counters["CAM-01"] = detector.settings.CLAUDE_ANALYSIS_INTERVAL - 1
    result = detector.analyze_frame("CAM-01", image)
    assert result.raw_detections[0]["label"] == "bottle"
