"""Tests for the cat detection module.

These tests verify Detection class behavior without requiring
actual jetson-inference or a GPU.
"""

import pytest

from src.camera.detector import Detection, CatDetector


class TestDetection:
    def make_detection(self, left=10, top=20, right=110, bottom=120,
                       frame_w=300, frame_h=300, class_name="cat",
                       confidence=0.9):
        return Detection(
            class_name=class_name,
            confidence=confidence,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            frame_width=frame_w,
            frame_height=frame_h,
        )

    def test_center_x(self):
        det = self.make_detection(left=100, right=200)
        assert det.center_x == 150.0

    def test_center_y(self):
        det = self.make_detection(top=50, bottom=150)
        assert det.center_y == 100.0

    def test_width(self):
        det = self.make_detection(left=10, right=110)
        assert det.width == 100

    def test_height(self):
        det = self.make_detection(top=20, bottom=120)
        assert det.height == 100

    def test_area(self):
        det = self.make_detection(left=0, top=0, right=100, bottom=50)
        assert det.area == 5000

    def test_center_x_normalized_left(self):
        """Object at left edge should be -1.0."""
        det = self.make_detection(left=0, right=10, frame_w=300)
        assert det.center_x_normalized < -0.9

    def test_center_x_normalized_center(self):
        """Object at center should be ~0.0."""
        det = self.make_detection(left=140, right=160, frame_w=300)
        assert abs(det.center_x_normalized) < 0.1

    def test_center_x_normalized_right(self):
        """Object at right edge should be ~1.0."""
        det = self.make_detection(left=290, right=300, frame_w=300)
        assert det.center_x_normalized > 0.9

    def test_size_normalized_small(self):
        """Small object should have small normalized size."""
        det = self.make_detection(left=0, top=0, right=10, bottom=10,
                                  frame_w=300, frame_h=300)
        assert det.size_normalized < 0.01

    def test_size_normalized_large(self):
        """Object filling the frame should have normalized size ~1.0."""
        det = self.make_detection(left=0, top=0, right=300, bottom=300,
                                  frame_w=300, frame_h=300)
        assert det.size_normalized == pytest.approx(1.0)

    def test_size_normalized_capped_at_one(self):
        """Normalized size should not exceed 1.0."""
        det = self.make_detection(left=-100, top=-100, right=400, bottom=400,
                                  frame_w=300, frame_h=300)
        assert det.size_normalized <= 1.0

    def test_repr(self):
        det = self.make_detection()
        s = repr(det)
        assert "cat" in s
        assert "conf=" in s

    def test_zero_frame_size(self):
        det = self.make_detection(frame_w=0, frame_h=0)
        assert det.size_normalized == 0.0


class TestCatDetector:
    def test_lazy_init(self):
        """Detector should not load the model until first detect() call."""
        detector = CatDetector()
        assert detector._net is None

    def test_get_fps_before_init(self):
        """get_fps should return 0 before model is loaded."""
        detector = CatDetector()
        assert detector.get_fps() == 0.0
