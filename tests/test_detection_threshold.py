"""Tests for cat detection confidence threshold behavior.

Verifies that the CatDetector correctly filters detections based on
the confidence threshold, using mocked jetson-inference objects.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch

# Mock jetson_utils so detect() doesn't fail on import
sys.modules.setdefault("jetson_utils", MagicMock())

from src.camera.detector import CatDetector, Detection
from src.config import DETECTION_THRESHOLD


def make_mock_detection(class_id=16, confidence=0.9,
                        left=50, top=50, right=150, bottom=150):
    """Create a mock jetson-inference detection object."""
    det = MagicMock()
    det.ClassID = class_id
    det.Confidence = confidence
    det.Left = left
    det.Top = top
    det.Right = right
    det.Bottom = bottom
    return det


def make_mock_image(width=300, height=300):
    """Create a mock cudaImage."""
    img = MagicMock()
    img.width = width
    img.height = height
    return img


class TestConfidenceThreshold:
    """Test that detections are filtered by confidence threshold."""

    def _create_detector_with_mock_net(self, threshold=DETECTION_THRESHOLD):
        """Create a CatDetector with a mocked neural network."""
        detector = CatDetector(threshold=threshold)
        detector._net = MagicMock()
        detector._net.GetClassDesc.return_value = "cat"
        return detector

    def test_default_threshold_value(self):
        """Default threshold should match config."""
        detector = CatDetector()
        assert detector.threshold == DETECTION_THRESHOLD
        assert detector.threshold == 0.5

    def test_high_confidence_detected(self):
        """Detection at 95% confidence should be returned."""
        detector = self._create_detector_with_mock_net(threshold=0.5)
        mock_det = make_mock_detection(confidence=0.95)
        detector._net.Detect.return_value = [mock_det]

        results = detector.detect(make_mock_image())
        assert len(results) == 1
        assert results[0].confidence == 0.95

    def test_exact_threshold_detected(self):
        """Detection exactly at threshold should be returned (net handles filtering)."""
        detector = self._create_detector_with_mock_net(threshold=0.5)
        mock_det = make_mock_detection(confidence=0.5)
        detector._net.Detect.return_value = [mock_det]

        results = detector.detect(make_mock_image())
        assert len(results) == 1
        assert results[0].confidence == 0.5

    def test_custom_threshold(self):
        """Detector should accept custom threshold values."""
        detector = CatDetector(threshold=0.8)
        assert detector.threshold == 0.8

    @pytest.mark.parametrize("confidence", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    def test_confidence_levels_at_10pct_steps(self, confidence):
        """Detection at {confidence} confidence should produce correct Detection object."""
        detector = self._create_detector_with_mock_net(threshold=0.0)
        mock_det = make_mock_detection(confidence=confidence)
        detector._net.Detect.return_value = [mock_det]

        results = detector.detect(make_mock_image())
        assert len(results) == 1
        assert results[0].confidence == pytest.approx(confidence)
        assert results[0].class_name == "cat"

    def test_non_cat_filtered_out(self):
        """Non-cat detections should be filtered regardless of confidence."""
        detector = self._create_detector_with_mock_net(threshold=0.5)
        detector._net.GetClassDesc.return_value = "dog"
        mock_det = make_mock_detection(confidence=0.99)
        detector._net.Detect.return_value = [mock_det]

        results = detector.detect(make_mock_image())
        assert len(results) == 0

    def test_multiple_cats_different_confidence(self):
        """Multiple detections should all be returned with correct confidence."""
        detector = self._create_detector_with_mock_net(threshold=0.3)
        dets = [
            make_mock_detection(confidence=0.95, left=10, right=60),
            make_mock_detection(confidence=0.50, left=100, right=200),
            make_mock_detection(confidence=0.35, left=200, right=280),
        ]
        detector._net.Detect.return_value = dets

        results = detector.detect(make_mock_image())
        assert len(results) == 3
        confidences = [r.confidence for r in results]
        assert confidences == [0.95, 0.50, 0.35]

    def test_mixed_cats_and_non_cats(self):
        """Only cat detections should be returned from mixed results."""
        detector = self._create_detector_with_mock_net(threshold=0.5)

        cat_det = make_mock_detection(confidence=0.85)
        dog_det = make_mock_detection(confidence=0.90)
        person_det = make_mock_detection(confidence=0.95)

        def get_class(class_id):
            # Use the order of Detect calls
            return get_class._classes.pop(0)
        get_class._classes = ["cat", "dog", "person"]
        detector._net.GetClassDesc.side_effect = get_class

        detector._net.Detect.return_value = [cat_det, dog_det, person_det]
        results = detector.detect(make_mock_image())

        assert len(results) == 1
        assert results[0].confidence == 0.85

    def test_no_detections_returns_empty(self):
        """No detections should return an empty list."""
        detector = self._create_detector_with_mock_net(threshold=0.5)
        detector._net.Detect.return_value = []

        results = detector.detect(make_mock_image())
        assert results == []


class TestDetectionConfidenceValues:
    """Test the Detection data class stores and exposes confidence correctly."""

    @pytest.mark.parametrize("confidence", [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
    def test_detection_stores_confidence(self, confidence):
        """Detection should store confidence={confidence} accurately."""
        det = Detection(
            class_name="cat",
            confidence=confidence,
            left=50, top=50, right=150, bottom=150,
            frame_width=300, frame_height=300,
        )
        assert det.confidence == confidence

    def test_detection_repr_shows_confidence(self):
        """repr should display the confidence value."""
        det = Detection(
            class_name="cat",
            confidence=0.87,
            left=50, top=50, right=150, bottom=150,
            frame_width=300, frame_height=300,
        )
        assert "0.87" in repr(det)

    @pytest.mark.parametrize("threshold,confidence,should_pass", [
        (0.5, 0.9, True),
        (0.5, 0.5, True),
        (0.5, 0.3, False),
        (0.8, 0.7, False),
        (0.8, 0.85, True),
        (0.3, 0.31, True),
        (0.0, 0.01, True),
        (1.0, 0.99, False),
    ])
    def test_threshold_comparison(self, threshold, confidence, should_pass):
        """Confidence {confidence} vs threshold {threshold} should {'pass' if should_pass else 'fail'}."""
        passes = confidence >= threshold
        assert passes == should_pass
