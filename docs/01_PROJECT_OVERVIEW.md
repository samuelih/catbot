# CatToy Robot - Project Overview

## What Is This?

CatToy is an autonomous robot that plays with your cat. It uses a camera to detect your cat, drives toward and around it with unpredictable movements, and avoids crashing into walls and furniture. You can also take manual control with a wireless gamepad.

## Hardware Platform

This project is built on the **Waveshare JetBot 2GB AI Kit**, which uses an NVIDIA Jetson Nano 2GB as its brain. The Jetson Nano is a small, low-power computer with a GPU that can run AI/machine learning models in real time.

**Important:** We are NOT using the JetBot's Jupyter notebook software. We are writing our own pure Python application from scratch.

### What's In the Kit

| Component | Purpose |
|-----------|---------|
| Jetson Nano 2GB Developer Kit | The "brain" - a small Linux computer with GPU |
| 64GB Micro SD Card | Storage for the operating system and our software |
| Metal box / chassis | The robot's body |
| IMX219-160 Camera | 8MP camera with 160-degree wide-angle lens (sees more) |
| Comfast CF-811AC V3 USB WiFi | Wireless networking (so you can SSH into the robot) |
| JetBot expansion board | Connects motors, batteries, and sensors to the Jetson |
| 2x DC Motors + 2x Wheels | Makes the robot move (differential drive = tank steering) |
| 2x Caster wheels | Small free-spinning wheels for balance |
| Wireless gamepad | Manual control override |
| 4010 cooling fan | Keeps the Jetson Nano cool during AI processing |
| 3x 18650 batteries (NOT included) | Power source - you need to buy these separately |
| 12.6V battery charger | Charges the 3S battery pack |

### How the Hardware Works Together

```
                    ┌─────────────────────────────┐
                    │      Jetson Nano 2GB         │
                    │   (Linux computer + GPU)     │
                    │                              │
  WiFi USB ────────>│ USB port     CSI port ──────>│<──── IMX219-160 Camera
  Gamepad USB ─────>│ USB port                     │
                    │                              │
                    │ I2C Bus 1 (Pins 3 & 5)       │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────┴───────────────────┐
                    │    JetBot Expansion Board     │
                    │                              │
                    │  PCA9685 (PWM controller)    │
                    │      ↓                       │
                    │  TB6612FNG (motor driver)    │
                    │      ↓          ↓            │
                    │  Left Motor  Right Motor     │
                    │                              │
                    │  INA219 (battery monitor)    │
                    │  SSD1306 OLED (status)       │
                    │  3x 18650 batteries          │
                    └──────────────────────────────┘
```

## Software Architecture

The software is a **state machine** that cycles between different behaviors:

```
                    ┌─────────┐
                    │  IDLE   │ ← Robot is still, waiting
                    └────┬────┘
                         │ Cat detected
                    ┌────┴────┐
              ┌────>│ SEEKING │ ← Spinning/scanning for cat
              │     └────┬────┘
              │          │ Cat in view
              │     ┌────┴────┐
              │     │ CHASING │ ← Moving toward/around cat
              │     └────┬────┘
              │          │ Obstacle detected
              │     ┌────┴────┐
              │     │AVOIDING │ ← Backing up, turning away
              │     └────┬────┘
              │          │ Clear
              └──────────┘

         Gamepad button press at ANY time
                    ↓
              ┌──────────┐
              │  MANUAL  │ ← Full gamepad control
              └──────────┘
```

### Key Design Decisions

1. **NVIDIA jetson-inference library** for cat detection: This is NVIDIA's official inference library that comes pre-optimized with TensorRT. It includes SSD-MobileNet-V2 trained on COCO dataset, which has a "cat" class (class ID 17). It handles all the GPU optimization automatically.

2. **Pure Python with smbus2** for motor control: Instead of using the heavy Adafruit libraries, we write directly to the PCA9685 registers over I2C. This gives us more control and fewer dependencies.

3. **GStreamer pipeline** for camera: The IMX219 camera uses NVIDIA's hardware-accelerated `nvarguscamerasrc` element, which is much faster than software-based capture.

4. **Collision avoidance priority**: The state machine ALWAYS prioritizes avoiding obstacles over chasing the cat. Safety first.

## Expected Performance

| Metric | Expected Value |
|--------|---------------|
| Cat detection FPS | 10-15 FPS (on Jetson Nano 2GB) |
| Detection latency | ~100ms per frame |
| Motor response time | <50ms |
| Battery life | ~2 hours (depends on battery capacity) |
| RAM usage | ~1.5GB of 2GB (tight - swap space recommended) |

## Prerequisites (What You Need to Buy)

- **3x 18650 lithium batteries** (3.7V, flat-top, unprotected, <67mm length)
- **Ethernet cable** (for initial setup before WiFi works)
- **Monitor + USB keyboard + mouse** (for initial OS setup, OR use headless setup)
- **Another computer** (to SSH into the Jetson Nano after setup)
- **Micro SD card reader** (to flash the OS image)
