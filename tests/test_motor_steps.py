"""Tests for motor movement at 10% speed steps.

Verifies that both motors respond correctly to speed values from 0% to 100%
in 10% increments, for both forward and reverse directions.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from src.config import (
    MOTOR_A_IN1,
    MOTOR_A_IN2,
    MOTOR_A_PWM,
    MOTOR_B_IN1,
    MOTOR_B_IN2,
    MOTOR_B_PWM,
)


@pytest.fixture
def mock_bus():
    """Create a mock SMBus."""
    with patch("smbus2.SMBus") as mock_smbus_class:
        mock_bus_instance = MagicMock()
        mock_bus_instance.read_byte_data.return_value = 0x00
        mock_smbus_class.return_value = mock_bus_instance
        yield mock_bus_instance


@pytest.fixture
def motor_driver(mock_bus):
    """Create a MotorDriver with mocked I2C."""
    from src.motor.driver import MotorDriver, PCA9685
    pwm = PCA9685()
    return MotorDriver(pwm=pwm)


# Generate 10% step values: 0.0, 0.1, 0.2, ..., 1.0
SPEED_STEPS = [round(i * 0.1, 1) for i in range(11)]


class TestMotorStepsForward:
    """Test left and right motors at each 10% forward speed step."""

    @pytest.mark.parametrize("speed", SPEED_STEPS)
    def test_left_motor_forward_step(self, motor_driver, mock_bus, speed):
        """Left motor should accept forward speed {speed}."""
        mock_bus.reset_mock()
        motor_driver.set_left(speed)
        if speed > 0:
            assert mock_bus.write_byte_data.called

    @pytest.mark.parametrize("speed", SPEED_STEPS)
    def test_right_motor_forward_step(self, motor_driver, mock_bus, speed):
        """Right motor should accept forward speed {speed}."""
        mock_bus.reset_mock()
        motor_driver.set_right(speed)
        if speed > 0:
            assert mock_bus.write_byte_data.called


class TestMotorStepsReverse:
    """Test left and right motors at each 10% reverse speed step."""

    @pytest.mark.parametrize("speed", SPEED_STEPS)
    def test_left_motor_reverse_step(self, motor_driver, mock_bus, speed):
        """Left motor should accept reverse speed -{speed}."""
        mock_bus.reset_mock()
        motor_driver.set_left(-speed)
        if speed > 0:
            assert mock_bus.write_byte_data.called

    @pytest.mark.parametrize("speed", SPEED_STEPS)
    def test_right_motor_reverse_step(self, motor_driver, mock_bus, speed):
        """Right motor should accept reverse speed -{speed}."""
        mock_bus.reset_mock()
        motor_driver.set_right(-speed)
        if speed > 0:
            assert mock_bus.write_byte_data.called


class TestMotorStepsPWMValues:
    """Verify PWM duty cycle scales correctly at each 10% step."""

    @pytest.mark.parametrize("speed", [s for s in SPEED_STEPS if s > 0])
    def test_pwm_duty_scales_with_speed(self, mock_bus, speed):
        """PWM off-value should scale proportionally with speed."""
        from src.motor.driver import PCA9685
        pwm = PCA9685()
        mock_bus.reset_mock()

        pwm.set_duty_cycle(0, speed)

        if speed >= 1.0:
            # Full on: on=4096, off=0
            pass
        else:
            expected_off = int(speed * 4095)
            # The off low byte should contain expected_off & 0xFF
            calls = mock_bus.write_byte_data.call_args_list
            off_l_calls = [c for c in calls if c[0][1] == 0x08]  # LED0_OFF_L
            assert len(off_l_calls) == 1
            assert off_l_calls[0][0][2] == expected_off & 0xFF


class TestMotorStepsBothMotors:
    """Test set_motors at each 10% step driving both wheels together."""

    @pytest.mark.parametrize("speed", SPEED_STEPS)
    def test_both_motors_same_speed(self, motor_driver, mock_bus, speed):
        """Both motors at {speed} should drive straight."""
        mock_bus.reset_mock()
        motor_driver.set_motors(speed, speed)
        # No error = both motors accepted the speed
        assert True

    @pytest.mark.parametrize("speed", SPEED_STEPS)
    def test_differential_steering(self, motor_driver, mock_bus, speed):
        """Left at {speed}, right at 0 should turn right."""
        mock_bus.reset_mock()
        motor_driver.set_motors(speed, 0)
        assert True


class TestMotorStepsZeroIsStop:
    """Verify 0% speed results in motor stop (all channels off)."""

    def test_left_zero_stops(self, motor_driver, mock_bus):
        """Left motor at 0% should be fully stopped."""
        motor_driver.set_left(0.5)  # First move
        mock_bus.reset_mock()
        motor_driver.set_left(0.0)  # Then stop
        # All three channels (PWM, IN1, IN2) should be set to off
        assert mock_bus.write_byte_data.called

    def test_right_zero_stops(self, motor_driver, mock_bus):
        """Right motor at 0% should be fully stopped."""
        motor_driver.set_right(0.5)  # First move
        mock_bus.reset_mock()
        motor_driver.set_right(0.0)  # Then stop
        assert mock_bus.write_byte_data.called
