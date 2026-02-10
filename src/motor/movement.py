"""
High-level movement patterns for the CatToy robot.

Builds on MotorDriver to provide behaviors like chase, spin, zigzag, etc.
Uses differential drive (tank steering): two independent motors.
"""

import random
import time

from src.config import (
    AVOIDANCE_BACKUP_SPEED,
    AVOIDANCE_COOLDOWN,
    CHASE_BASE_SPEED,
    CHASE_MAX_SPEED,
    CHASE_STEERING_GAIN,
    MAX_SPEED,
    MIN_SPEED,
    SEEKING_SPEED,
)
from src.motor.driver import MotorDriver
from src.utils.logger import setup_logger

logger = setup_logger("motor.movement")


class MovementController:
    """High-level movement patterns using differential drive."""

    def __init__(self, motor_driver=None):
        self.motors = motor_driver or MotorDriver()
        self._last_zigzag_time = 0
        self._zigzag_direction = 1

    def _clamp_speed(self, speed):
        """Clamp speed to configured limits."""
        if abs(speed) < MIN_SPEED:
            return 0.0
        return max(-MAX_SPEED, min(MAX_SPEED, speed))

    def forward(self, speed=CHASE_BASE_SPEED):
        """Drive straight forward."""
        speed = self._clamp_speed(speed)
        self.motors.set_motors(speed, speed)

    def backward(self, speed=AVOIDANCE_BACKUP_SPEED):
        """Drive straight backward."""
        speed = self._clamp_speed(speed)
        self.motors.set_motors(-speed, -speed)

    def spin_left(self, speed=SEEKING_SPEED):
        """Spin in place to the left (counterclockwise from above)."""
        speed = self._clamp_speed(speed)
        self.motors.set_motors(-speed, speed)

    def spin_right(self, speed=SEEKING_SPEED):
        """Spin in place to the right (clockwise from above)."""
        speed = self._clamp_speed(speed)
        self.motors.set_motors(speed, -speed)

    def steer(self, forward_speed, turn_amount):
        """Drive forward with steering.

        Args:
            forward_speed: Base forward speed (0.0 to 1.0).
            turn_amount: Steering (-1.0 = full left, 0.0 = straight, 1.0 = full right).
        """
        left = forward_speed + turn_amount * CHASE_STEERING_GAIN
        right = forward_speed - turn_amount * CHASE_STEERING_GAIN
        left = self._clamp_speed(left)
        right = self._clamp_speed(right)
        self.motors.set_motors(left, right)

    def chase_target(self, target_x_normalized, target_size_normalized):
        """Chase a detected target based on its position and size in the frame.

        Args:
            target_x_normalized: Horizontal position (-1.0=left edge, 0.0=center, 1.0=right edge).
            target_size_normalized: How much of the frame the target fills (0.0=tiny, 1.0=fills frame).
        """
        # Steering: proportional to how far off-center the target is
        turn = target_x_normalized

        # Speed: inversely proportional to target size (slow down when close)
        if target_size_normalized > 0.4:
            speed = CHASE_BASE_SPEED * 0.5
        elif target_size_normalized > 0.2:
            speed = CHASE_BASE_SPEED
        else:
            speed = CHASE_MAX_SPEED

        # Add slight zigzag randomness to be more interesting to the cat
        now = time.time()
        if now - self._last_zigzag_time > 0.5:
            self._last_zigzag_time = now
            if random.random() < 0.3:
                self._zigzag_direction *= -1

        zigzag = self._zigzag_direction * 0.05
        turn += zigzag

        self.steer(speed, turn)
        logger.debug(
            "Chase: speed=%.2f turn=%.2f (target_x=%.2f size=%.2f)",
            speed, turn, target_x_normalized, target_size_normalized,
        )

    def avoid_obstacle(self):
        """Execute obstacle avoidance maneuver: back up and turn."""
        logger.info("Avoiding obstacle: backing up")
        self.backward(AVOIDANCE_BACKUP_SPEED)
        time.sleep(AVOIDANCE_COOLDOWN * 0.5)

        # Turn randomly left or right
        if random.random() > 0.5:
            self.spin_left(AVOIDANCE_BACKUP_SPEED)
        else:
            self.spin_right(AVOIDANCE_BACKUP_SPEED)
        time.sleep(AVOIDANCE_COOLDOWN * 0.5)

        self.stop()

    def stop(self):
        """Stop all motors."""
        self.motors.stop()

    def cleanup(self):
        """Release hardware resources."""
        self.motors.cleanup()
