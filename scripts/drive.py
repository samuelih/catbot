#!/usr/bin/env python3
"""
Manual drive control for CatToy via gamepad or keyboard.

Run on the Jetson (via SSH):
    python3 scripts/drive.py

Gamepad controls (TGZ Controller):
    Left stick    - Drive (Y=forward/back, X=steering)
    Right stick   - Tank steering (overrides left stick)
    A button      - Boost (1.5x speed)
    B button      - Emergency stop
    Start/Home    - Quit

Keyboard fallback:
    Arrow keys    - Drive
    W/S           - Increase/decrease speed
    Space         - Stop
    Q/Esc         - Quit
"""

import sys
import select
import tty
import termios
import time
import math

from src.motor.driver import MotorDriver
from src.control.gamepad import Gamepad

# --- Tuning ---
SPEED_STEP = 0.1
MIN_SPEED = 0.2
MAX_SPEED = 1.0
DEFAULT_SPEED = 0.5
LOOP_HZ = 30

# Stick deadzone (ignore values below this)
DEADZONE = 0.15

# Exponential response curve: higher = more precision at low stick, more punch at full
# 1.0 = linear, 2.0 = quadratic, 3.0 = cubic
EXPO = 2.5

# Smoothing factor: 0.0 = no smoothing (instant), 1.0 = never changes
# Lower = more responsive, higher = smoother
SMOOTHING = 0.4

# Reduce turn sensitivity relative to forward (prevents spinning out)
TURN_SCALE = 0.6


def apply_deadzone(val, dz=DEADZONE):
    """Apply deadzone and rescale so output starts at 0 just outside the zone."""
    if abs(val) < dz:
        return 0.0
    sign = 1.0 if val > 0 else -1.0
    return sign * (abs(val) - dz) / (1.0 - dz)


def apply_expo(val, exp=EXPO):
    """Apply exponential curve for finer low-speed control."""
    return math.copysign(abs(val) ** exp, val)


def lerp(current, target, factor):
    """Linear interpolation for smooth ramping."""
    return current + (target - current) * (1.0 - factor)


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

    # Smoothed motor outputs
    smooth_left = 0.0
    smooth_right = 0.0

    # Keyboard target speeds (held until space/release)
    kb_left = 0.0
    kb_right = 0.0

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
    print(f"  Motors: L=+0.00  R=+0.00")

    def update_display():
        print(f"\033[7;1H  Speed: {speed:.0%}   ")
        print(f"  State: {current.upper():20s}")
        print(f"  Input: {source:20s}")
        print(f"  Motors: L={smooth_left:+.2f}  R={smooth_right:+.2f}   ")
        sys.stdout.flush()

    try:
        while True:
            target_left = 0.0
            target_right = 0.0
            gp = gamepad.state

            # --- Gamepad input ---
            if gp.connected and gamepad.has_input():
                source = 'gamepad'

                # B = emergency stop (immediate, no smoothing)
                if gp.button_b:
                    motors.stop()
                    smooth_left = 0.0
                    smooth_right = 0.0
                    current = 'E-STOP'
                    update_display()
                    time.sleep(1.0 / LOOP_HZ)
                    continue

                boost = 1.5 if gp.button_a else 1.0

                # Apply deadzone + expo to stick axes
                fwd_raw = apply_deadzone(-gp.left_y)
                turn_raw = apply_deadzone(gp.left_x)

                forward = apply_expo(fwd_raw) * speed * boost
                turn = apply_expo(turn_raw) * speed * boost * TURN_SCALE

                target_left = forward + turn
                target_right = forward - turn

                # Right stick overrides for tank steering
                ry = apply_deadzone(-gp.right_y)
                rx = apply_deadzone(-gp.right_x)
                if abs(ry) > 0 or abs(rx) > 0:
                    target_left = apply_expo(ry) * speed * boost
                    target_right = apply_expo(rx) * speed * boost

                target_left = max(-1.0, min(1.0, target_left))
                target_right = max(-1.0, min(1.0, target_right))

            # --- Keyboard input ---
            key = read_key_nonblocking()
            if key is not None:
                source = 'keyboard'

                if key in ('q', 'Q', 'ESC'):
                    break
                elif key == 'UP':
                    kb_left = speed
                    kb_right = speed
                elif key == 'DOWN':
                    kb_left = -speed
                    kb_right = -speed
                elif key == 'LEFT':
                    kb_left = -speed
                    kb_right = speed
                elif key == 'RIGHT':
                    kb_left = speed
                    kb_right = -speed
                elif key in ('w', 'W'):
                    speed = min(MAX_SPEED, round(speed + SPEED_STEP, 1))
                elif key in ('s', 'S'):
                    speed = max(MIN_SPEED, round(speed - SPEED_STEP, 1))
                elif key == ' ':
                    kb_left = 0.0
                    kb_right = 0.0

            # Use keyboard targets if gamepad isn't active
            if not (gp.connected and gamepad.has_input()):
                target_left = kb_left
                target_right = kb_right

            # --- Smooth ramp toward target ---
            smooth_left = lerp(smooth_left, target_left, SMOOTHING)
            smooth_right = lerp(smooth_right, target_right, SMOOTHING)

            # Snap to zero if very close (prevents motor whine at near-zero)
            if abs(smooth_left) < 0.05:
                smooth_left = 0.0
            if abs(smooth_right) < 0.05:
                smooth_right = 0.0

            motors.set_motors(smooth_left, smooth_right)

            if abs(smooth_left) > 0.01 or abs(smooth_right) > 0.01:
                current = f'L={smooth_left:+.2f} R={smooth_right:+.2f}'
            else:
                current = 'stop'

            update_display()

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
