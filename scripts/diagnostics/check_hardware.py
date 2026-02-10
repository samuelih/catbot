#!/usr/bin/env python3
"""
CatToy Hardware Diagnostics

Checks all hardware components and reports their status.
Run this after setup to verify everything is working:

    python3 scripts/diagnostics/check_hardware.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_i2c():
    """Check I2C bus and known devices."""
    print("\n--- I2C Bus ---")
    try:
        import smbus2
        bus = smbus2.SMBus(1)

        devices = {
            0x3C: "SSD1306 OLED Display",
            0x40: "PCA9685 PWM Controller (motors)",
            0x41: "INA219 Battery Monitor",
            0x70: "PCA9685 ALL CALL",
        }

        found = []
        for addr in range(0x03, 0x78):
            try:
                bus.read_byte(addr)
                name = devices.get(addr, "Unknown")
                found.append((addr, name))
            except OSError:
                pass

        bus.close()

        if not found:
            print("  [FAIL] No I2C devices found on bus 1!")
            print("         Check expansion board connection to 40-pin header.")
            return False

        all_ok = True
        for addr, name in found:
            print(f"  [OK]   0x{addr:02X} - {name}")

        for addr, name in devices.items():
            if addr not in [a for a, _ in found]:
                print(f"  [MISS] 0x{addr:02X} - {name} NOT FOUND")
                if addr == 0x40:
                    all_ok = False  # PCA9685 is critical

        return all_ok

    except ImportError:
        print("  [FAIL] smbus2 not installed: pip3 install smbus2")
        return False
    except PermissionError:
        print("  [FAIL] Permission denied. Run with sudo or add user to i2c group.")
        return False
    except Exception as e:
        print(f"  [FAIL] I2C error: {e}")
        return False


def check_camera():
    """Check CSI camera."""
    print("\n--- Camera ---")

    # Check device node
    if os.path.exists("/dev/video0"):
        print("  [OK]   /dev/video0 exists")
    else:
        print("  [FAIL] /dev/video0 not found!")
        print("         Check CSI ribbon cable (blue side toward HDMI port).")
        return False

    # Try to capture a frame
    try:
        from src.camera.capture import Camera
        cam = Camera(use_jetson_utils=False)
        frame = cam.capture()
        cam.close()

        if frame is not None:
            h, w = frame.shape[:2]
            print(f"  [OK]   Camera capture works ({w}x{h})")
            return True
        else:
            print("  [FAIL] Camera returned empty frame")
            return False
    except Exception as e:
        print(f"  [WARN] Camera test failed: {e}")
        print("         This may be OK if no display is connected.")
        return True  # Not necessarily a failure on headless setup


def check_jetson_inference():
    """Check if jetson-inference is installed."""
    print("\n--- jetson-inference ---")
    try:
        import jetson_inference
        import jetson_utils
        print("  [OK]   jetson_inference is installed")
        print("  [OK]   jetson_utils is installed")
        return True
    except ImportError:
        print("  [FAIL] jetson-inference not installed!")
        print("         See docs/03_SOFTWARE_INSTALLATION.md")
        return False


def check_python_deps():
    """Check Python dependencies."""
    print("\n--- Python Dependencies ---")
    deps = {
        "smbus2": "I2C motor control",
        "evdev": "Gamepad input",
        "numpy": "Math/image processing",
        "cv2": "OpenCV (camera, collision avoidance)",
        "PIL": "Pillow (image utilities)",
    }

    all_ok = True
    for module, purpose in deps.items():
        try:
            __import__(module)
            print(f"  [OK]   {module} - {purpose}")
        except ImportError:
            print(f"  [FAIL] {module} - {purpose} NOT INSTALLED")
            all_ok = False

    return all_ok


def check_gamepad():
    """Check for gamepad/joystick devices."""
    print("\n--- Gamepad ---")
    try:
        import evdev
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        gamepads = []
        for dev in devices:
            caps = dev.capabilities(verbose=True)
            for cap_name, events in caps.items():
                if cap_name == ('EV_ABS', 3):
                    gamepads.append(dev)
                    break

        if gamepads:
            for gp in gamepads:
                print(f"  [OK]   {gp.name} ({gp.path})")
            return True
        else:
            print("  [INFO] No gamepad detected (optional - needed for manual control)")
            return True  # Not a failure
    except ImportError:
        print("  [WARN] evdev not installed. Gamepad check skipped.")
        return True
    except Exception as e:
        print(f"  [WARN] Gamepad check error: {e}")
        return True


def check_system():
    """Check system configuration."""
    print("\n--- System ---")

    # Check swap
    with open("/proc/meminfo") as f:
        meminfo = f.read()
    swap_total = 0
    for line in meminfo.split("\n"):
        if line.startswith("SwapTotal:"):
            swap_total = int(line.split()[1]) // 1024  # MB
            break

    if swap_total > 0:
        print(f"  [OK]   Swap: {swap_total} MB")
    else:
        print("  [WARN] No swap configured! The 2GB Nano NEEDS swap.")
        print("         Run: sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile")

    # Check RAM
    for line in meminfo.split("\n"):
        if line.startswith("MemTotal:"):
            mem_total = int(line.split()[1]) // 1024
            print(f"  [INFO] RAM: {mem_total} MB")
            break

    # Check GPU
    try:
        with open("/sys/devices/gpu.0/load") as f:
            gpu_load = int(f.read().strip()) / 10.0
        print(f"  [INFO] GPU load: {gpu_load}%")
    except Exception:
        pass

    return True


def main():
    print("=" * 50)
    print("  CatToy Hardware Diagnostics")
    print("=" * 50)

    results = {
        "I2C Bus": check_i2c(),
        "Camera": check_camera(),
        "jetson-inference": check_jetson_inference(),
        "Python Deps": check_python_deps(),
        "Gamepad": check_gamepad(),
        "System": check_system(),
    }

    print("\n" + "=" * 50)
    print("  Summary")
    print("=" * 50)

    all_ok = True
    for name, ok in results.items():
        status = "[OK]  " if ok else "[FAIL]"
        print(f"  {status} {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n  All checks passed! Ready to run.")
        print("  Start with: python3 src/main.py")
    else:
        print("\n  Some checks failed. Review the output above.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
