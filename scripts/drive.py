#!/usr/bin/env python3
"""
Manual keyboard drive control for CatToy.

Run on the Jetson (via SSH):
    python3 scripts/drive.py

Controls:
    Arrow Up    - Forward
    Arrow Down  - Backward
    Arrow Left  - Spin left
    Arrow Right - Spin right
    W/S         - Increase/decrease speed
    Space       - Stop
    Q/Esc       - Quit
"""

import sys
import tty
import termios
import time

from src.motor.driver import MotorDriver

SPEED_STEP = 0.1
MIN_SPEED = 0.2
MAX_SPEED = 1.0
DEFAULT_SPEED = 0.4


def read_key():
    """Read a single keypress, handling arrow key escape sequences."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                return {
                    'A': 'UP',
                    'B': 'DOWN',
                    'C': 'RIGHT',
                    'D': 'LEFT',
                }.get(ch3, None)
            return 'ESC'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    motors = MotorDriver()
    speed = DEFAULT_SPEED
    current = 'stop'

    print("\033[2J\033[H")  # clear screen
    print("=== CatToy Drive Mode ===")
    print()
    print("  Arrow keys  - Drive")
    print("  W/S         - Speed up/down")
    print("  Space       - Stop")
    print("  Q/Esc       - Quit")
    print()
    print(f"  Speed: {speed:.0%}")
    print(f"  State: STOPPED")

    def update_display():
        # Move cursor to speed/state lines and overwrite
        print(f"\033[8;1H  Speed: {speed:.0%}   ")
        print(f"  State: {current.upper():20s}")
        sys.stdout.flush()

    try:
        while True:
            key = read_key()
            if key is None:
                continue

            if key in ('q', 'Q', 'ESC'):
                break
            elif key == 'UP':
                motors.set_motors(speed, speed)
                current = 'forward'
            elif key == 'DOWN':
                motors.set_motors(-speed, -speed)
                current = 'reverse'
            elif key == 'LEFT':
                motors.set_motors(-speed, speed)
                current = 'spin left'
            elif key == 'RIGHT':
                motors.set_motors(speed, -speed)
                current = 'spin right'
            elif key in ('w', 'W'):
                speed = min(MAX_SPEED, round(speed + SPEED_STEP, 1))
            elif key in ('s', 'S'):
                speed = max(MIN_SPEED, round(speed - SPEED_STEP, 1))
            elif key == ' ':
                motors.stop()
                current = 'stop'

            update_display()
    except KeyboardInterrupt:
        pass
    finally:
        print("\033[11;1H\nStopping motors...")
        motors.stop()
        motors.cleanup()
        print("Done.")


if __name__ == "__main__":
    main()
