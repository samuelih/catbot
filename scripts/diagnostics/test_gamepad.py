#!/usr/bin/env python3
"""
Gamepad Test Script

Displays real-time gamepad input to help identify button/axis mappings.

    python3 scripts/diagnostics/test_gamepad.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.control.gamepad import Gamepad


def main():
    print("=" * 50)
    print("  CatToy Gamepad Test")
    print("=" * 50)
    print()
    print("Plug in the wireless gamepad USB receiver.")
    print("Move sticks and press buttons to see input values.")
    print("Press Ctrl+C to exit.")
    print()

    gamepad = Gamepad()

    if not gamepad.state.connected:
        print("[FAIL] No gamepad found!")
        print()
        print("Troubleshooting:")
        print("  1. Is the USB receiver plugged in?")
        print("  2. Is the gamepad powered on?")
        print("  3. Check: ls /dev/input/")
        print("  4. Check: sudo evtest")
        return 1

    gamepad.start()
    print("Gamepad connected! Displaying input...\n")

    try:
        while True:
            s = gamepad.state
            sys.stdout.write(
                f"\rLX:{s.left_x:+.2f} LY:{s.left_y:+.2f} "
                f"RX:{s.right_x:+.2f} RY:{s.right_y:+.2f} "
                f"A:{int(s.button_a)} B:{int(s.button_b)} "
                f"X:{int(s.button_x)} Y:{int(s.button_y)} "
                f"HOME:{int(s.button_home)}  "
            )
            sys.stdout.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n\nGamepad test ended.")
    finally:
        gamepad.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
