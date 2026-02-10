"""Tests for the collision avoidance system."""

import numpy as np
import pytest
from unittest.mock import patch

from src.avoidance.collision import CollisionDetector


@pytest.fixture
def detector():
    return CollisionDetector()


class TestCollisionDetector:
    def test_clear_frame_no_obstacle(self, detector):
        """A plain gray frame should not trigger obstacle detection."""
        frame = np.full((300, 300, 3), 128, dtype=np.uint8)
        is_obstacle, density = detector.check_obstacle(frame)
        assert not is_obstacle
        assert density < 0.1

    def test_busy_frame_detects_obstacle(self, detector):
        """A frame with many edges should trigger obstacle detection."""
        frame = np.zeros((300, 300, 3), dtype=np.uint8)
        # Create a checkerboard pattern in the bottom third (many edges)
        bottom_start = int(300 * 0.65)
        for y in range(bottom_start, 300):
            for x in range(300):
                if (x // 5 + y // 5) % 2 == 0:
                    frame[y, x] = [255, 255, 255]

        is_obstacle, density = detector.check_obstacle(frame)
        assert is_obstacle
        assert density > 0.3

    def test_returns_tuple(self, detector):
        """check_obstacle should return (bool, float)."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = detector.check_obstacle(frame)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)

    def test_edge_density_range(self, detector):
        """Edge density should be between 0 and 1."""
        frame = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
        _, density = detector.check_obstacle(frame)
        assert 0.0 <= density <= 1.0

    def test_grayscale_input(self, detector):
        """Should handle grayscale input."""
        frame = np.zeros((100, 100), dtype=np.uint8)
        is_obstacle, density = detector.check_obstacle(frame)
        assert isinstance(is_obstacle, bool)

    def test_non_numpy_input_returns_safe(self, detector):
        """Non-numpy input without jetson_utils should return safe (no obstacle)."""
        is_obstacle, density = detector.check_obstacle("not_an_image")
        assert not is_obstacle
        assert density == 0.0
