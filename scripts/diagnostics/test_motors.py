#!/usr/bin/env python3
"""
Motor Test Script

Tests each motor individually and then together.
USE WITH CAUTION - the robot will move!

Place the robot on a raised surface with wheels off the ground,
or be ready to grab it.

    python3 scripts/diagnostics/test_motors.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.motor.driver import MotorDriver


def main():
    print("=" * 50)
    print("  CatToy Motor Test")
    print("=" * 50)
    print()
    print("WARNING: The robot will move! Place it on a raised")
    print("surface with wheels off the ground for safety.")
    print()

    response = input("Press Enter to start (or Ctrl+C to cancel): ")

    driver = MotorDriver()
    speed = 0.3  # Low speed for testing

    try:
        # Test left motor forward
        print("\n1. Left motor FORWARD (3 seconds)...")
        driver.set_left(speed)
        time.sleep(3)
        driver.stop()
        time.sleep(1)

        # Test left motor reverse
        print("2. Left motor REVERSE (3 seconds)...")
        driver.set_left(-speed)
        time.sleep(3)
        driver.stop()
        time.sleep(1)

        # Test right motor forward
        print("3. Right motor FORWARD (3 seconds)...")
        driver.set_right(speed)
        time.sleep(3)
        driver.stop()
        time.sleep(1)

        # Test right motor reverse
        print("4. Right motor REVERSE (3 seconds)...")
        driver.set_right(-speed)
        time.sleep(3)
        driver.stop()
        time.sleep(1)

        # Test both forward
        print("5. Both motors FORWARD (3 seconds)...")
        driver.set_motors(speed, speed)
        time.sleep(3)
        driver.stop()
        time.sleep(1)

        # Test spin right
        print("6. Spin RIGHT (3 seconds)...")
        driver.set_motors(speed, -speed)
        time.sleep(3)
        driver.stop()
        time.sleep(1)

        # Test spin left
        print("7. Spin LEFT (3 seconds)...")
        driver.set_motors(-speed, speed)
        time.sleep(3)
        driver.stop()

        print("\nMotor test complete!")
        print()
        print("Expected behavior:")
        print("  - Steps 1-2: Left wheel spins forward then backward")
        print("  - Steps 3-4: Right wheel spins forward then backward")
        print("  - Step 5: Robot drives forward")
        print("  - Step 6: Robot spins clockwise (right)")
        print("  - Step 7: Robot spins counter-clockwise (left)")
        print()
        print("If motors are reversed, swap MOTOR_A/B assignments in src/config.py")
        print("If a motor spins the wrong direction, swap its IN1/IN2 channels in src/config.py")

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        driver.cleanup()
        print("Motors stopped and cleaned up.")


if __name__ == "__main__":
    main()
