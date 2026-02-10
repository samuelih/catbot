"""
Cat detection using NVIDIA jetson-inference with SSD-MobileNet-V2.

Uses the COCO-trained model which includes "cat" as one of its 90 classes.
The model runs through TensorRT for real-time performance on Jetson Nano.
"""

from src.config import CAT_CLASS_NAME, DETECTION_MODEL, DETECTION_THRESHOLD
from src.utils.logger import setup_logger

logger = setup_logger("camera.detector")


class Detection:
    """Represents a single detected object."""

    def __init__(self, class_name, confidence, left, top, right, bottom,
                 frame_width, frame_height):
        self.class_name = class_name
        self.confidence = confidence
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.frame_width = frame_width
        self.frame_height = frame_height

    @property
    def center_x(self):
        """Center X coordinate in pixels."""
        return (self.left + self.right) / 2.0

    @property
    def center_y(self):
        """Center Y coordinate in pixels."""
        return (self.top + self.bottom) / 2.0

    @property
    def width(self):
        """Bounding box width in pixels."""
        return self.right - self.left

    @property
    def height(self):
        """Bounding box height in pixels."""
        return self.bottom - self.top

    @property
    def area(self):
        """Bounding box area in pixels."""
        return self.width * self.height

    @property
    def center_x_normalized(self):
        """Center X normalized to [-1.0, 1.0] (left edge to right edge)."""
        return (self.center_x / self.frame_width) * 2.0 - 1.0

    @property
    def center_y_normalized(self):
        """Center Y normalized to [-1.0, 1.0] (top to bottom)."""
        return (self.center_y / self.frame_height) * 2.0 - 1.0

    @property
    def size_normalized(self):
        """Fraction of the frame area occupied by this detection (0.0 to 1.0)."""
        frame_area = self.frame_width * self.frame_height
        if frame_area == 0:
            return 0.0
        return min(1.0, self.area / frame_area)

    def __repr__(self):
        return (
            f"Detection({self.class_name}, conf={self.confidence:.2f}, "
            f"pos=({self.center_x:.0f},{self.center_y:.0f}), "
            f"size={self.size_normalized:.3f})"
        )


class CatDetector:
    """Detects cats in camera frames using jetson-inference detectNet.

    On first use, the model is loaded and a TensorRT engine is built.
    This initial build can take several minutes but only happens once.
    The engine is cached to disk for subsequent runs.
    """

    def __init__(self, model=DETECTION_MODEL, threshold=DETECTION_THRESHOLD):
        """Initialize the detector.

        Args:
            model: Model name (e.g., "ssd-mobilenet-v2").
            threshold: Minimum confidence for detections (0.0-1.0).
        """
        self.model_name = model
        self.threshold = threshold
        self._net = None
        self._frame_width = 0
        self._frame_height = 0

    def _lazy_init(self):
        """Load the model on first use (avoids import-time GPU allocation)."""
        if self._net is not None:
            return

        try:
            from jetson_inference import detectNet

            logger.info(
                "Loading detection model '%s' (threshold=%.2f). "
                "First run builds TensorRT engine (may take several minutes)...",
                self.model_name,
                self.threshold,
            )
            self._net = detectNet(self.model_name, threshold=self.threshold)
            logger.info("Detection model loaded successfully")
        except ImportError:
            raise ImportError(
                "jetson-inference is not installed. "
                "See docs/03_SOFTWARE_INSTALLATION.md for instructions."
            )

    def detect(self, image):
        """Run detection on a camera frame.

        Args:
            image: A jetson_utils.cudaImage from Camera.capture().

        Returns:
            List of Detection objects for all detected cats.
        """
        self._lazy_init()

        from jetson_utils import cudaImage

        detections = self._net.Detect(image)

        self._frame_width = image.width
        self._frame_height = image.height

        cats = []
        for det in detections:
            class_name = self._net.GetClassDesc(det.ClassID)
            if class_name == CAT_CLASS_NAME:
                cats.append(
                    Detection(
                        class_name=class_name,
                        confidence=det.Confidence,
                        left=det.Left,
                        top=det.Top,
                        right=det.Right,
                        bottom=det.Bottom,
                        frame_width=self._frame_width,
                        frame_height=self._frame_height,
                    )
                )

        if cats:
            logger.debug("Detected %d cat(s): %s", len(cats), cats)

        return cats

    def detect_all(self, image):
        """Run detection and return ALL objects (not just cats).

        Useful for debugging to see what the model detects.

        Args:
            image: A jetson_utils.cudaImage.

        Returns:
            List of Detection objects for all detected objects.
        """
        self._lazy_init()

        detections = self._net.Detect(image)

        self._frame_width = image.width
        self._frame_height = image.height

        results = []
        for det in detections:
            class_name = self._net.GetClassDesc(det.ClassID)
            results.append(
                Detection(
                    class_name=class_name,
                    confidence=det.Confidence,
                    left=det.Left,
                    top=det.Top,
                    right=det.Right,
                    bottom=det.Bottom,
                    frame_width=self._frame_width,
                    frame_height=self._frame_height,
                )
            )

        return results

    def get_fps(self):
        """Get the current inference FPS (from TensorRT)."""
        if self._net is not None:
            return self._net.GetNetworkFPS()
        return 0.0
