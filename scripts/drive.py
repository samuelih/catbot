#!/usr/bin/env python3
"""
Manual drive control for CatToy via gamepad or keyboard.

Run on the Jetson (via SSH):
    python3 scripts/drive.py

Gamepad controls (TGZ Controller):
    Left stick    - Drive (Y=forward/back, X=steering)
    Right stick   - Tank steering (overrides left stick)
    D-pad         - Discrete forward/back/spin
    A button      - Boost (double speed)
    B button      - Emergency stop
    Start         - Quit

Keyboard fallback:
    Arrow keys    - Drive
    W/S           - Increase/decrease speed
    Space         - Stop
    Q/Esc         - Quit
"""

import sys
import os
import select
import tty
import termios
import time

from src.motor.driver import MotorDriver
from src.control.gamepad import Gamepad

SPEED_STEP = 0.1
MIN_SPEED = 0.2
MAX_SPEED = 1.0
DEFAULT_SPEED = 0.4
LOOP_HZ = 20


def read_key_nonblocking():
    """Non-blocking keypress read. Returns None if no key pressed."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        return {'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT'}.get(ch3)
                return 'ESC'
            return ch
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    motors = MotorDriver()
    gamepad = Gamepad()

    if gamepad.state.connected:
        gamepad.start()

    speed = DEFAULT_SPEED
    current = 'stop'
    source = 'gamepad' if gamepad.state.connected else 'keyboard'

    print("\033[2J\033[H")  # clear screen
    print("=== CatToy Drive Mode ===")
    print()
    if gamepad.state.connected:
        print("  Gamepad: CONNECTED (left stick to drive, B=stop, Start=quit)")
    else:
        print("  Gamepad: not found (using keyboard)")
    print("  Keyboard: arrows=drive, W/S=speed, Space=stop, Q=quit")
    print()
    print(f"  Speed: {speed:.0%}")
    print(f"  State: STOPPED")
    print(f"  Input: {source}")
    print(f"  L(+0.00,+0.00) R(+0.00,+0.00)")

    def update_display(lx=0, ly=0, rx=0, ry=0):
        print(f"\033[7;1H  Speed: {speed:.0%}   ")
        print(f"  State: {current.upper():20s}")
        print(f"  Input: {source:20s}")
        print(f"  L({lx:+.2f},{ly:+.2f}) R({rx:+.2f},{ry:+.2f})   ")
        sys.stdout.flush()

    try:
        while True:
            left_speed = 0.0
            right_speed = 0.0
            gp = gamepad.state

            # --- Gamepad input ---
            if gp.connected and gamepad.has_input():
                source = 'gamepad'

                # B = emergency stop
                if gp.button_b:
                    motors.stop()
                    current = 'E-STOP'
                    update_display(gp.left_x, gp.left_y, gp.right_x, gp.right_y)
                    time.sleep(1.0 / LOOP_HZ)
                    continue

                boost = 1.5 if gp.button_a else 1.0

                # Left stick: arcade drive (Y=forward/back, X=turn)
                forward = -gp.left_y  # stick up = negative Y = forward
                turn = gp.left_x

                left_speed = (forward + turn) * speed * boost
                right_speed = (forward - turn) * speed * boost

                # Right stick overrides for tank steering
                if abs(gp.right_x) > 0.1 or abs(gp.right_y) > 0.1:
                    left_speed = -gp.right_y * speed * boost
                    right_speed = -gp.right_x * speed * boost  # RZ maps to right Y

                left_speed = max(-1.0, min(1.0, left_speed))
                right_speed = max(-1.0, min(1.0, right_speed))

                motors.set_motors(left_speed, right_speed)
                if abs(left_speed) > 0.01 or abs(right_speed) > 0.01:
                    current = f'L={left_speed:+.1f} R={right_speed:+.1f}'
                else:
                    current = 'stop'

                update_display(gp.left_x, gp.left_y, gp.right_x, gp.right_y)

            # --- Keyboard input ---
            key = read_key_nonblocking()
            if key is not None:
                source = 'keyboard'

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

                update_display(gp.left_x, gp.left_y, gp.right_x, gp.right_y)

            # Check Start button for quit
            if gp.connected and gp.button_home:
                break

            time.sleep(1.0 / LOOP_HZ)

    except KeyboardInterrupt:
        pass
    finally:
        print("\033[12;1H\nStopping motors...")
        motors.stop()
        motors.cleanup()
        gamepad.stop()
        print("Done.")


if __name__ == "__main__":
    main()
