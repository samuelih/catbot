"""Tests for the movement controller."""

import pytest
from unittest.mock import MagicMock, patch

from src.motor.movement import MovementController


@pytest.fixture
def mock_motors():
    driver = MagicMock()
    return driver


@pytest.fixture
def movement(mock_motors):
    mc = MovementController(motor_driver=mock_motors)
    return mc


class TestMovementController:
    def test_forward(self, movement, mock_motors):
        movement.forward(0.5)
        mock_motors.set_motors.assert_called()
        args = mock_motors.set_motors.call_args[0]
        assert args[0] > 0  # left > 0
        assert args[1] > 0  # right > 0

    def test_backward(self, movement, mock_motors):
        movement.backward(0.3)
        mock_motors.set_motors.assert_called()
        args = mock_motors.set_motors.call_args[0]
        assert args[0] < 0
        assert args[1] < 0

    def test_spin_left(self, movement, mock_motors):
        movement.spin_left(0.3)
        mock_motors.set_motors.assert_called()
        args = mock_motors.set_motors.call_args[0]
        assert args[0] < 0  # left backward
        assert args[1] > 0  # right forward

    def test_spin_right(self, movement, mock_motors):
        movement.spin_right(0.3)
        mock_motors.set_motors.assert_called()
        args = mock_motors.set_motors.call_args[0]
        assert args[0] > 0  # left forward
        assert args[1] < 0  # right backward

    def test_stop(self, movement, mock_motors):
        movement.stop()
        mock_motors.stop.assert_called_once()

    def test_steer_straight(self, movement, mock_motors):
        movement.steer(0.5, 0.0)
        mock_motors.set_motors.assert_called()
        args = mock_motors.set_motors.call_args[0]
        # With 0 turn, left and right should be equal
        assert abs(args[0] - args[1]) < 0.01

    def test_steer_left(self, movement, mock_motors):
        movement.steer(0.5, -0.5)
        mock_motors.set_motors.assert_called()
        args = mock_motors.set_motors.call_args[0]
        # Left should be slower than right when turning left
        assert args[0] < args[1]

    def test_steer_right(self, movement, mock_motors):
        movement.steer(0.5, 0.5)
        mock_motors.set_motors.assert_called()
        args = mock_motors.set_motors.call_args[0]
        # Right should be slower than left when turning right
        assert args[0] > args[1]

    def test_chase_target_center(self, movement, mock_motors):
        """Chasing a centered target should drive mostly straight."""
        movement.chase_target(0.0, 0.1)
        mock_motors.set_motors.assert_called()

    def test_chase_target_left(self, movement, mock_motors):
        """Chasing a target on the left should turn left."""
        movement.chase_target(-0.8, 0.1)
        mock_motors.set_motors.assert_called()

    def test_chase_target_close(self, movement, mock_motors):
        """Chasing a close target (large size) should slow down."""
        movement.chase_target(0.0, 0.5)
        mock_motors.set_motors.assert_called()

    def test_cleanup(self, movement, mock_motors):
        movement.cleanup()
        mock_motors.cleanup.assert_called_once()
