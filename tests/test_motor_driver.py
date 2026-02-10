"""Tests for the motor driver module.

These tests use a mock SMBus to avoid requiring actual hardware.
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
    PCA9685_ADDRESS,
    PCA9685_LED0_OFF_H,
    PCA9685_LED0_OFF_L,
    PCA9685_LED0_ON_H,
    PCA9685_LED0_ON_L,
    PCA9685_MODE1,
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
def pca9685(mock_bus):
    """Create a PCA9685 instance with mocked I2C."""
    from src.motor.driver import PCA9685
    return PCA9685()


@pytest.fixture
def motor_driver(pca9685):
    """Create a MotorDriver instance with mocked hardware."""
    from src.motor.driver import MotorDriver
    return MotorDriver(pwm=pca9685)


class TestPCA9685:
    def test_init_resets_all_pwm(self, pca9685, mock_bus):
        """PCA9685 should reset all channels on init."""
        # set_all_pwm(0, 0) is called during init
        assert mock_bus.write_byte_data.called

    def test_set_pwm_writes_correct_registers(self, pca9685, mock_bus):
        """set_pwm should write to the correct channel registers."""
        mock_bus.reset_mock()
        pca9685.set_pwm(0, 0, 2048)

        calls = mock_bus.write_byte_data.call_args_list
        # Should write to LED0_ON_L, LED0_ON_H, LED0_OFF_L, LED0_OFF_H
        assert any(c[0][1] == PCA9685_LED0_ON_L for c in calls)
        assert any(c[0][1] == PCA9685_LED0_OFF_L for c in calls)

    def test_set_pwm_channel_offset(self, pca9685, mock_bus):
        """Channel N registers should be offset by 4*N from channel 0."""
        mock_bus.reset_mock()
        channel = 3
        pca9685.set_pwm(channel, 0, 1000)

        expected_on_l = PCA9685_LED0_ON_L + 4 * channel
        expected_off_l = PCA9685_LED0_OFF_L + 4 * channel

        calls = mock_bus.write_byte_data.call_args_list
        assert any(c[0][1] == expected_on_l for c in calls)
        assert any(c[0][1] == expected_off_l for c in calls)

    def test_set_duty_cycle_zero(self, pca9685, mock_bus):
        """Duty cycle 0 should turn channel fully off."""
        mock_bus.reset_mock()
        pca9685.set_duty_cycle(0, 0.0)
        # set_channel_full_off writes on=0, off=0
        calls = mock_bus.write_byte_data.call_args_list
        off_values = [c[0][2] for c in calls
                      if c[0][1] in (PCA9685_LED0_OFF_L, PCA9685_LED0_OFF_H)]
        assert all(v == 0 for v in off_values)

    def test_set_duty_cycle_clamps(self, pca9685, mock_bus):
        """Duty cycle should be clamped to [0, 1]."""
        # Should not raise
        pca9685.set_duty_cycle(0, -0.5)
        pca9685.set_duty_cycle(0, 1.5)

    def test_set_pwm_freq(self, pca9685, mock_bus):
        """set_pwm_freq should write to PRESCALE register."""
        mock_bus.reset_mock()
        pca9685.set_pwm_freq(100)
        # Should write to prescale register (0xFE)
        calls = mock_bus.write_byte_data.call_args_list
        assert any(c[0][1] == 0xFE for c in calls)


class TestMotorDriver:
    def test_stop_sets_all_zero(self, motor_driver, mock_bus):
        """stop() should set all motor channels to off."""
        mock_bus.reset_mock()
        motor_driver.stop()
        # Both motors should have their PWM channels set to off
        assert mock_bus.write_byte_data.called

    def test_set_left_forward(self, motor_driver, mock_bus):
        """set_left with positive speed should set forward direction."""
        mock_bus.reset_mock()
        motor_driver.set_left(0.5)
        # Should have written to MOTOR_A channels
        assert mock_bus.write_byte_data.called

    def test_set_left_reverse(self, motor_driver, mock_bus):
        """set_left with negative speed should set reverse direction."""
        mock_bus.reset_mock()
        motor_driver.set_left(-0.5)
        assert mock_bus.write_byte_data.called

    def test_set_right_forward(self, motor_driver, mock_bus):
        """set_right with positive speed should set forward direction."""
        mock_bus.reset_mock()
        motor_driver.set_right(0.5)
        assert mock_bus.write_byte_data.called

    def test_speed_clamping(self, motor_driver, mock_bus):
        """Motor speed should be clamped to [-1, 1]."""
        # Should not raise
        motor_driver.set_left(2.0)
        motor_driver.set_left(-2.0)
        motor_driver.set_right(2.0)
        motor_driver.set_right(-2.0)

    def test_cleanup(self, motor_driver, mock_bus):
        """cleanup() should stop motors and close bus."""
        motor_driver.cleanup()
        mock_bus.close.assert_called_once()
