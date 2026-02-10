"""
Wireless gamepad input handling.

Reads input from the USB wireless gamepad using the evdev library.
Translates joystick/button events into motor commands.
"""

import threading

from src.config import GAMEPAD_DEADZONE
from src.utils.logger import setup_logger

logger = setup_logger("control.gamepad")


class GamepadState:
    """Holds the current state of all gamepad inputs."""

    def __init__(self):
        self.left_x = 0.0   # Left stick X: -1.0 (left) to 1.0 (right)
        self.left_y = 0.0   # Left stick Y: -1.0 (up/forward) to 1.0 (down/back)
        self.right_x = 0.0  # Right stick X
        self.right_y = 0.0  # Right stick Y
        self.button_a = False
        self.button_b = False
        self.button_x = False
        self.button_y = False
        self.button_home = False
        self.connected = False


class Gamepad:
    """Reads input from a USB wireless gamepad.

    Runs a background thread that continuously reads gamepad events.
    The current state is always available via the .state attribute.

    Usage:
        gamepad = Gamepad()
        if gamepad.state.connected:
            forward = -gamepad.state.left_y  # Negate: stick up = forward
            turn = gamepad.state.left_x
    """

    def __init__(self):
        self.state = GamepadState()
        self._device = None
        self._thread = None
        self._running = False
        self._find_device()

    def _find_device(self):
        """Find the first available gamepad/joystick device."""
        try:
            import evdev
        except ImportError:
            logger.warning(
                "evdev not installed. Gamepad disabled. "
                "Install with: pip3 install evdev"
            )
            return

        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            caps = device.capabilities(verbose=True)
            # Look for devices with absolute axes (joysticks)
            for cap_name, events in caps.items():
                if cap_name == ('EV_ABS', 3):
                    self._device = device
                    self.state.connected = True
                    logger.info("Gamepad found: %s (%s)", device.name, device.path)
                    return

        logger.info("No gamepad detected. Manual control disabled.")

    def start(self):
        """Start the background input reading thread."""
        if self._device is None:
            return

        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        logger.info("Gamepad input thread started")

    def _read_loop(self):
        """Background loop reading gamepad events."""
        import evdev

        try:
            for event in self._device.read_loop():
                if not self._running:
                    break

                if event.type == evdev.ecodes.EV_ABS:
                    self._handle_axis(event.code, event.value)
                elif event.type == evdev.ecodes.EV_KEY:
                    self._handle_button(event.code, event.value)
        except OSError:
            logger.warning("Gamepad disconnected")
            self.state.connected = False

    def _normalize_axis(self, value, min_val=0, max_val=255):
        """Normalize an axis value to -1.0 to 1.0 range."""
        center = (min_val + max_val) / 2.0
        half_range = (max_val - min_val) / 2.0
        if half_range == 0:
            return 0.0
        normalized = (value - center) / half_range
        # Apply deadzone
        if abs(normalized) < GAMEPAD_DEADZONE:
            return 0.0
        return max(-1.0, min(1.0, normalized))

    def _handle_axis(self, code, value):
        """Process an axis event."""
        import evdev

        # Common axis codes - may need adjustment for your specific gamepad
        if code == evdev.ecodes.ABS_X:
            self.state.left_x = self._normalize_axis(value)
        elif code == evdev.ecodes.ABS_Y:
            self.state.left_y = self._normalize_axis(value)
        elif code == evdev.ecodes.ABS_RX or code == evdev.ecodes.ABS_Z:
            self.state.right_x = self._normalize_axis(value)
        elif code == evdev.ecodes.ABS_RY or code == evdev.ecodes.ABS_RZ:
            self.state.right_y = self._normalize_axis(value)

    def _handle_button(self, code, value):
        """Process a button event (value: 1=pressed, 0=released)."""
        import evdev

        pressed = value == 1

        # Common button codes - may need adjustment
        if code == evdev.ecodes.BTN_SOUTH or code == evdev.ecodes.BTN_A:
            self.state.button_a = pressed
        elif code == evdev.ecodes.BTN_EAST or code == evdev.ecodes.BTN_B:
            self.state.button_b = pressed
        elif code == evdev.ecodes.BTN_NORTH or code == evdev.ecodes.BTN_X:
            self.state.button_x = pressed
        elif code == evdev.ecodes.BTN_WEST or code == evdev.ecodes.BTN_Y:
            self.state.button_y = pressed
        elif code == evdev.ecodes.BTN_MODE:
            self.state.button_home = pressed

        if pressed:
            logger.debug("Button pressed: code=%d", code)

    def has_input(self):
        """Check if any significant gamepad input is currently active."""
        if not self.state.connected:
            return False
        return (
            abs(self.state.left_x) > GAMEPAD_DEADZONE
            or abs(self.state.left_y) > GAMEPAD_DEADZONE
            or abs(self.state.right_x) > GAMEPAD_DEADZONE
            or self.state.button_a
            or self.state.button_b
        )

    def stop(self):
        """Stop the background input thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
