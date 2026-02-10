"""Tests for configuration values."""

import pytest
from src.config import (
    AVOIDANCE_COOLDOWN,
    AVOIDANCE_EDGE_THRESHOLD,
    AVOIDANCE_PIXEL_THRESHOLD,
    BATTERY_FULL_VOLTAGE,
    BATTERY_LOW_VOLTAGE,
    CAMERA_CAPTURE_HEIGHT,
    CAMERA_CAPTURE_WIDTH,
    CAMERA_FRAMERATE,
    CHASE_BASE_SPEED,
    CHASE_MAX_SPEED,
    DETECTION_THRESHOLD,
    I2C_BUS,
    MAX_SPEED,
    MIN_SPEED,
    MOTOR_A_IN1,
    MOTOR_A_IN2,
    MOTOR_A_INA,
    MOTOR_A_INB,
    MOTOR_A_PWM,
    MOTOR_B_IN1,
    MOTOR_B_IN2,
    MOTOR_B_INA,
    MOTOR_B_INB,
    MOTOR_B_PWM,
    MOTOR_PWM_FREQ,
    PCA9685_ADDRESS,
)


def test_i2c_bus_valid():
    assert I2C_BUS in (0, 1)


def test_pca9685_address_range():
    assert 0x40 <= PCA9685_ADDRESS <= 0x7F


def test_motor_channels_unique():
    channels = [MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2, MOTOR_A_INA, MOTOR_A_INB,
                MOTOR_B_PWM, MOTOR_B_IN1, MOTOR_B_IN2, MOTOR_B_INA, MOTOR_B_INB]
    assert len(set(channels)) == 10, "Motor channels must be unique"


def test_motor_channels_in_range():
    for ch in [MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2, MOTOR_A_INA, MOTOR_A_INB,
               MOTOR_B_PWM, MOTOR_B_IN1, MOTOR_B_IN2, MOTOR_B_INA, MOTOR_B_INB]:
        assert 0 <= ch <= 15, f"Channel {ch} out of PCA9685 range"


def test_pwm_freq_valid():
    assert 24 <= MOTOR_PWM_FREQ <= 1600


def test_speed_limits():
    assert 0.0 < MIN_SPEED < MAX_SPEED <= 1.0
    assert CHASE_BASE_SPEED <= CHASE_MAX_SPEED


def test_camera_resolution_valid():
    assert CAMERA_CAPTURE_WIDTH > 0
    assert CAMERA_CAPTURE_HEIGHT > 0
    assert CAMERA_FRAMERATE > 0


def test_detection_threshold_range():
    assert 0.0 < DETECTION_THRESHOLD < 1.0


def test_avoidance_config_valid():
    assert 0.0 < AVOIDANCE_PIXEL_THRESHOLD < 1.0
    assert AVOIDANCE_EDGE_THRESHOLD > 0
    assert AVOIDANCE_COOLDOWN > 0


def test_battery_voltages():
    assert BATTERY_LOW_VOLTAGE < BATTERY_FULL_VOLTAGE
    assert BATTERY_LOW_VOLTAGE > 0
