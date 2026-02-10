"""
Collision avoidance using camera-based edge detection.

Analyzes the lower portion of the camera frame for edges/details
that indicate nearby obstacles. Does not require depth sensing -
works by detecting high-frequency content that appears when objects
are close to the camera.
"""

import numpy as np

from src.config import (
    AVOIDANCE_EDGE_THRESHOLD,
    AVOIDANCE_PIXEL_THRESHOLD,
    AVOIDANCE_ZONE_TOP_RATIO,
)
from src.utils.logger import setup_logger

logger = setup_logger("avoidance.collision")


class CollisionDetector:
    """Detects obstacles using edge density in the lower portion of the frame.

    How it works:
    - The bottom third of the camera frame is analyzed
    - A Canny edge detector finds edges (outlines of objects)
    - When many edges appear in the avoidance zone, something is close
    - The threshold is tuned to trigger at approximately 30cm distance

    This is a simple but effective approach that doesn't need depth sensors.
    It works because close objects produce more visual detail (edges) than
    distant ones.
    """

    def __init__(self):
        self._cv2 = None

    def _lazy_import_cv2(self):
        if self._cv2 is None:
            import cv2
            self._cv2 = cv2

    def check_obstacle(self, frame):
        """Check if there's an obstacle in the camera frame.

        Args:
            frame: A numpy array (BGR image from OpenCV) OR a
                   jetson_utils.cudaImage. If cudaImage, it will be
                   converted to numpy automatically.

        Returns:
            Tuple of (is_obstacle: bool, edge_density: float).
            edge_density ranges from 0.0 (clear) to 1.0 (obstacle).
        """
        self._lazy_import_cv2()
        cv2 = self._cv2

        # Convert from CUDA image to numpy if needed
        if not isinstance(frame, np.ndarray):
            try:
                from jetson_utils import cudaToNumpy
                frame = cudaToNumpy(frame)
            except (ImportError, Exception):
                logger.warning("Cannot convert frame for collision detection")
                return False, 0.0

        height, width = frame.shape[:2]

        # Extract the avoidance zone (bottom portion of frame)
        zone_top = int(height * AVOIDANCE_ZONE_TOP_RATIO)
        avoidance_zone = frame[zone_top:, :]

        # Convert to grayscale
        if len(avoidance_zone.shape) == 3:
            gray = cv2.cvtColor(avoidance_zone, cv2.COLOR_BGR2GRAY)
        else:
            gray = avoidance_zone

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Canny edge detection
        edges = cv2.Canny(blurred, AVOIDANCE_EDGE_THRESHOLD,
                          AVOIDANCE_EDGE_THRESHOLD * 2)

        # Calculate edge density (fraction of pixels that are edges)
        total_pixels = edges.shape[0] * edges.shape[1]
        if total_pixels == 0:
            return False, 0.0

        edge_pixels = np.count_nonzero(edges)
        edge_density = float(edge_pixels / total_pixels)

        is_obstacle = bool(edge_density > AVOIDANCE_PIXEL_THRESHOLD)

        if is_obstacle:
            logger.info(
                "OBSTACLE DETECTED (edge_density=%.3f, threshold=%.3f)",
                edge_density,
                AVOIDANCE_PIXEL_THRESHOLD,
            )

        return is_obstacle, edge_density

    def check_obstacle_cuda(self, cuda_image):
        """Check for obstacles directly from a CUDA image.

        This is a convenience wrapper that handles the CUDA-to-numpy conversion.

        Args:
            cuda_image: A jetson_utils.cudaImage.

        Returns:
            Tuple of (is_obstacle: bool, edge_density: float).
        """
        return self.check_obstacle(cuda_image)
