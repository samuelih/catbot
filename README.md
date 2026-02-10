# CatToy

Autonomous cat toy robot built on the **Waveshare JetBot 2GB AI Kit**. Uses AI-powered cat detection (SSD-MobileNet-V2 via TensorRT) to chase your cat around, with camera-based collision avoidance and wireless gamepad override.

## Hardware

- NVIDIA Jetson Nano 2GB Developer Kit
- IMX219-160 CSI camera (160-degree FOV)
- 2x DC motors via PCA9685 PWM + TB6612FNG H-bridge (I2C)
- Comfast CF-811AC V3 USB WiFi (RTL8811CU)
- Wireless USB gamepad
- 3x 18650 battery pack

## Quick Start

**On the Jetson Nano:**

```bash
# 1. Clone the project
git clone <your-repo-url> cattoy
cd cattoy

# 2. Run the setup script (installs all dependencies, builds jetson-inference)
sudo bash scripts/setup/install_dependencies.sh

# 3. Install the WiFi driver (if using CF-811AC V3)
sudo bash scripts/setup/install_wifi_driver.sh

# 4. Verify hardware is working
python3 scripts/diagnostics/check_hardware.py

# 5. Test individual components
python3 scripts/diagnostics/test_motors.py
python3 scripts/diagnostics/test_camera.py

# 6. Run the cat toy!
python3 src/main.py
```

## Usage

```bash
# Autonomous mode (default) - seeks and chases cats
python3 src/main.py

# Manual gamepad control only
python3 src/main.py --mode manual

# Lower detection threshold (detect cats at lower confidence)
python3 src/main.py --threshold 0.3

# Limit top speed
python3 src/main.py --speed 0.4

# Debug logging
python3 src/main.py --debug

# Disable collision avoidance (for testing in open areas)
python3 src/main.py --no-avoidance
```

## How It Works

The robot operates as a **finite state machine**:

```
IDLE ──(timeout)──> SEEKING ──(cat detected)──> CHASING
  ^                    |                            |
  |                    |                            |
  |              (obstacle!)                  (obstacle!)
  |                    v                            v
  └───────────── AVOIDING <─────────────────── AVOIDING
```

**MANUAL** mode overrides everything when the gamepad is active (press B for emergency stop).

| State    | What Happens                                         |
|----------|------------------------------------------------------|
| IDLE     | Motors off, waiting before starting to seek           |
| SEEKING  | Spinning left/right looking for a cat                 |
| CHASING  | Driving toward detected cat, speed based on distance  |
| AVOIDING | Backing up and turning away from obstacle              |
| MANUAL   | Direct gamepad control of both motors                 |

## Architecture

```
src/
  main.py              - Entry point, main loop
  config.py            - All hardware/tuning constants
  camera/
    capture.py         - GStreamer camera capture (IMX219 CSI)
    detector.py        - Cat detection (SSD-MobileNet-V2 + TensorRT)
  motor/
    driver.py          - PCA9685 + TB6612FNG motor driver (raw I2C)
    movement.py        - High-level movement patterns
  avoidance/
    collision.py       - Edge-based obstacle detection
  control/
    gamepad.py         - USB gamepad input (evdev)
    state_machine.py   - Behavioral state machine
  utils/
    logger.py          - Logging setup
```

## Tests

Tests run on any machine (no Jetson hardware required):

```bash
# Run all tests
python3 -m pytest tests/

# Single test file
python3 -m pytest tests/test_movement.py -v

# Single test
python3 -m pytest tests/test_state_machine.py::TestStateMachine::test_starts_in_idle -v
```

## Documentation

See the `docs/` directory for detailed guides:

1. **[Project Overview](docs/01_PROJECT_OVERVIEW.md)** - Architecture and design
2. **[Jetson Nano Setup](docs/02_JETSON_NANO_SETUP.md)** - First boot, Linux basics, SSH
3. **[Software Installation](docs/03_SOFTWARE_INSTALLATION.md)** - Dependencies, jetson-inference
4. **[Hardware Reference](docs/04_HARDWARE_REFERENCE.md)** - Pin mappings, I2C addresses, specs
5. **[Usage Guide](docs/05_USAGE_GUIDE.md)** - Running, tuning, troubleshooting

## Calibration

Edit `src/config.py` to tune behavior:

- `MOTOR_A_TRIM` / `MOTOR_B_TRIM` - Compensate if the robot drives crooked
- `MAX_SPEED` - Limit top speed (start low, increase gradually)
- `DETECTION_THRESHOLD` - Lower = more sensitive (more false positives)
- `AVOIDANCE_PIXEL_THRESHOLD` - Lower = more cautious obstacle avoidance
- `CHASE_STEERING_GAIN` - How aggressively it steers toward the cat

## License

This project is provided as-is for personal, educational use.
