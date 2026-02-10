"""
Camera capture using GStreamer pipeline for the IMX219-160 CSI camera.

Uses NVIDIA's nvarguscamerasrc for hardware-accelerated capture on Jetson Nano.
Falls back to jetson_utils.videoSource if available (from jetson-inference).
"""

import numpy as np

from src.config import (
    CAMERA_CAPTURE_HEIGHT,
    CAMERA_CAPTURE_WIDTH,
    CAMERA_DISPLAY_HEIGHT,
    CAMERA_DISPLAY_WIDTH,
    CAMERA_FLIP_METHOD,
    CAMERA_FRAMERATE,
)
from src.utils.logger import setup_logger

logger = setup_logger("camera.capture")


def build_gstreamer_pipeline(
    capture_width=CAMERA_CAPTURE_WIDTH,
    capture_height=CAMERA_CAPTURE_HEIGHT,
    display_width=CAMERA_DISPLAY_WIDTH,
    display_height=CAMERA_DISPLAY_HEIGHT,
    framerate=CAMERA_FRAMERATE,
    flip_method=CAMERA_FLIP_METHOD,
):
    """Build a GStreamer pipeline string for the IMX219 CSI camera.

    Returns:
        GStreamer pipeline string suitable for cv2.VideoCapture().
    """
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )


class Camera:
    """Manages the CSI camera capture.

    Provides frames as numpy arrays (BGR format) suitable for OpenCV
    or jetson-inference processing.
    """

    def __init__(self, use_jetson_utils=True):
        """Initialize the camera.

        Args:
            use_jetson_utils: If True, try to use jetson_utils.videoSource
                (better integration with jetson-inference). Falls back to
                OpenCV GStreamer if unavailable.
        """
        self._jetson_camera = None
        self._cv_camera = None

        if use_jetson_utils:
            try:
                from jetson_utils import videoSource

                self._jetson_camera = videoSource("csi://0")
                logger.info(
                    "Camera initialized via jetson_utils (CSI)"
                )
                return
            except (ImportError, Exception) as e:
                logger.warning(
                    "jetson_utils not available (%s), falling back to OpenCV", e
                )

        import cv2

        pipeline = build_gstreamer_pipeline()
        self._cv_camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not self._cv_camera.isOpened():
            raise RuntimeError(
                "Failed to open camera. Check CSI ribbon cable connection "
                "and run: ls /dev/video*"
            )
        logger.info("Camera initialized via OpenCV GStreamer pipeline")

    def capture(self):
        """Capture a single frame.

        Returns:
            For jetson_utils: a jetson_utils.cudaImage (GPU memory).
            For OpenCV: a numpy array in BGR format, or None on failure.
        """
        if self._jetson_camera is not None:
            img = self._jetson_camera.Capture()
            if img is None:
                logger.warning("Camera capture returned None (timeout)")
            return img

        if self._cv_camera is not None:
            ret, frame = self._cv_camera.read()
            if not ret:
                logger.warning("OpenCV camera read failed")
                return None
            return frame

        return None

    def is_open(self):
        """Check if the camera is currently open and capturing."""
        if self._jetson_camera is not None:
            return True
        if self._cv_camera is not None:
            return self._cv_camera.isOpened()
        return False

    def close(self):
        """Release camera resources."""
        if self._cv_camera is not None:
            self._cv_camera.release()
            self._cv_camera = None
        self._jetson_camera = None
        logger.info("Camera released")
