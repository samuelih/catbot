# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CatToy is an autonomous cat toy robot built on the Waveshare JetBot 2GB AI Kit (Jetson Nano 2GB). It uses computer vision for cat detection and camera-based edge-detection collision avoidance. The software is pure Python — no Jupyter notebooks, no Adafruit libraries.

## Target Hardware

- **Board**: NVIDIA Jetson Nano 2GB Developer Kit (JetPack 4.6.6, Ubuntu 18.04, kernel 4.9.x-tegra)
- **Camera**: IMX219-160 (160-degree FOV, CSI interface)
- **Motors**: 2x JGB37-520 DC motors via PCA9685 PWM (I2C 0x60) + TB6612FNG dual H-bridge
- **WiFi**: Comfast CF-811AC V3 USB adapter (RTL8811CU chipset, driver: ColdZoo/rtl8821cu-nvidia-jetson-nano)
- **Power**: 3x 18650 batteries (11.1V nominal)
- **Gamepad**: Wireless USB gamepad (manual override)
- **Other I2C**: INA219 battery monitor (0x41), SSD1306 OLED (0x3C)

## Build & Run Commands

```bash
# Install all dependencies on Jetson Nano
sudo bash scripts/setup/install_dependencies.sh

# Install WiFi driver (RTL8811CU for CF-811AC V3)
sudo bash scripts/setup/install_wifi_driver.sh

# Run the cat toy (main entry point)
python3 src/main.py

# Run with manual gamepad control
python3 src/main.py --mode manual

# Run tests (works on any machine, no hardware needed)
python3 -m pytest tests/
python3 -m pytest tests/test_motor_driver.py -v                           # single test file
python3 -m pytest tests/test_state_machine.py::TestStateMachine::test_starts_in_idle -v  # single test

# Hardware diagnostics
python3 scripts/diagnostics/check_hardware.py
python3 scripts/diagnostics/test_motors.py
python3 scripts/diagnostics/test_camera.py
python3 scripts/diagnostics/test_gamepad.py
```

## Architecture

```
src/
  main.py              — Entry point, main state-machine loop
  config.py            — All hardware addresses, pins, thresholds, tuning
  camera/
    capture.py         — GStreamer pipeline (nvarguscamerasrc) for IMX219 CSI
    detector.py        — Cat detection: SSD-MobileNet-V2 via jetson-inference (TensorRT)
  motor/
    driver.py          — PCA9685 I2C driver (smbus2) + TB6612FNG motor control
    movement.py        — High-level patterns: chase_target, avoid_obstacle, steer, spin
  avoidance/
    collision.py       — Canny edge density in lower frame = obstacle proximity
  control/
    gamepad.py         — evdev-based USB gamepad input (background thread)
    state_machine.py   — FSM: IDLE → SEEKING → CHASING → AVOIDING, MANUAL override
  utils/
    logger.py          — Logging configuration
```

## Key Design Decisions

- **Raw I2C via smbus2**: Motor driver talks directly to PCA9685 registers — no Adafruit/CircuitPython dependency stack. Channel mapping: 0=PWMA, 1=AIN2, 2=AIN1, 3=BIN1, 4=BIN2, 5=PWMB.
- **jetson-inference (not TensorFlow)**: Uses pure TensorRT via dusty-nv's jetson-inference for cat detection. SSD-MobileNet-V2 runs at ~10-15 FPS on Nano 2GB. The model loads lazily on first `detect()` call.
- **GStreamer camera pipeline**: Uses `nvarguscamerasrc` (Jetson-specific hardware-accelerated) with fallback to OpenCV GStreamer.
- **State machine separation**: `StateMachine` only manages state logic, never touches hardware directly. `main.py` reads state and commands motors accordingly.
- **Edge-based collision avoidance**: No depth sensor needed. Canny edge detection on the bottom 35% of the frame — high edge density means something is close.
- **Gamepad override**: MANUAL state overrides all autonomous behavior. Button B = emergency stop.

## Hardware Constraints

- 2GB RAM — requires 4GB swap, disable desktop GUI, only one model loaded at a time
- CSI camera at `/dev/video0`; must use `nvarguscamerasrc` GStreamer element
- I2C bus 1 (`/dev/i2c-1`): PCA9685 at 0x60, INA219 at 0x41, SSD1306 at 0x3C
- WiFi adapter needs `usb_modeswitch` (device appears as CD-ROM 0bda:1a2b before switching to 0bda:c811)
- JetPack 4.6.6 is EOL; kernel 4.9.x means many upstream drivers need backported forks

## Testing

Tests are designed to run on any machine (macOS/Linux) without Jetson hardware:
- Motor tests use mocked SMBus
- Movement tests use mocked MotorDriver
- Collision tests use synthetic numpy frames
- State machine tests use time patching
- Detector tests verify the Detection data class math without loading the model

68 tests total across 6 test files. Run with `python3 -m pytest tests/ -v`.
