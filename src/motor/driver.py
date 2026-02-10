"""
Low-level PCA9685 + TB6612FNG motor driver.

Communicates directly with the PCA9685 PWM controller over I2C
to control two DC motors via the TB6612FNG dual H-bridge driver.

This module does NOT depend on any Adafruit libraries. It writes
directly to PCA9685 registers using smbus2.
"""

import math
import time

import smbus2

from src.config import (
    I2C_BUS,
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
    PCA9685_ADDRESS,
    PCA9685_ALL_LED_OFF_L,
    PCA9685_ALL_LED_ON_L,
    PCA9685_ALLCALL,
    PCA9685_LED0_OFF_H,
    PCA9685_LED0_OFF_L,
    PCA9685_LED0_ON_H,
    PCA9685_LED0_ON_L,
    PCA9685_MODE1,
    PCA9685_MODE2,
    PCA9685_OSC_FREQ,
    PCA9685_OUTDRV,
    PCA9685_PRESCALE,
    PCA9685_RESTART,
    PCA9685_SLEEP,
)
from src.utils.logger import setup_logger

logger = setup_logger("motor.driver")


class PCA9685:
    """Direct I2C driver for the PCA9685 16-channel PWM controller."""

    def __init__(self, bus_num=I2C_BUS, address=PCA9685_ADDRESS):
        self.address = address
        self.bus = smbus2.SMBus(bus_num)
        self._init_device()

    def _init_device(self):
        """Initialize the PCA9685 to a known state."""
        self.set_all_pwm(0, 0)
        self.bus.write_byte_data(self.address, PCA9685_MODE2, PCA9685_OUTDRV)
        self.bus.write_byte_data(self.address, PCA9685_MODE1, PCA9685_ALLCALL)
        time.sleep(0.005)

        mode1 = self.bus.read_byte_data(self.address, PCA9685_MODE1)
        mode1 = mode1 & ~PCA9685_SLEEP
        self.bus.write_byte_data(self.address, PCA9685_MODE1, mode1)
        time.sleep(0.005)
        logger.debug("PCA9685 initialized at address 0x%02X", self.address)

    def set_pwm_freq(self, freq_hz):
        """Set the PWM frequency in Hz.

        Args:
            freq_hz: Desired frequency (24-1526 Hz).
        """
        prescale_val = PCA9685_OSC_FREQ / 4096.0 / float(freq_hz) - 1.0
        prescale = int(math.floor(prescale_val + 0.5))

        old_mode = self.bus.read_byte_data(self.address, PCA9685_MODE1)
        new_mode = (old_mode & 0x7F) | PCA9685_SLEEP
        self.bus.write_byte_data(self.address, PCA9685_MODE1, new_mode)
        self.bus.write_byte_data(self.address, PCA9685_PRESCALE, prescale)
        self.bus.write_byte_data(self.address, PCA9685_MODE1, old_mode)
        time.sleep(0.005)
        self.bus.write_byte_data(
            self.address, PCA9685_MODE1, old_mode | PCA9685_RESTART
        )
        logger.debug("PWM frequency set to %d Hz (prescale=%d)", freq_hz, prescale)

    def set_pwm(self, channel, on, off):
        """Set PWM on/off values for a single channel.

        Args:
            channel: PCA9685 channel (0-15).
            on: 12-bit value (0-4095) for rising edge.
            off: 12-bit value (0-4095) for falling edge.
        """
        self.bus.write_byte_data(
            self.address, PCA9685_LED0_ON_L + 4 * channel, on & 0xFF
        )
        self.bus.write_byte_data(
            self.address, PCA9685_LED0_ON_H + 4 * channel, on >> 8
        )
        self.bus.write_byte_data(
            self.address, PCA9685_LED0_OFF_L + 4 * channel, off & 0xFF
        )
        self.bus.write_byte_data(
            self.address, PCA9685_LED0_OFF_H + 4 * channel, off >> 8
        )

    def set_all_pwm(self, on, off):
        """Set PWM values for all channels simultaneously."""
        self.bus.write_byte_data(
            self.address, PCA9685_ALL_LED_ON_L, on & 0xFF
        )
        self.bus.write_byte_data(
            self.address, PCA9685_ALL_LED_ON_L + 1, on >> 8
        )
        self.bus.write_byte_data(
            self.address, PCA9685_ALL_LED_OFF_L, off & 0xFF
        )
        self.bus.write_byte_data(
            self.address, PCA9685_ALL_LED_OFF_L + 1, off >> 8
        )

    def set_channel_full_on(self, channel):
        """Set a channel to fully on (100% duty cycle)."""
        self.set_pwm(channel, 4096, 0)

    def set_channel_full_off(self, channel):
        """Set a channel to fully off (0% duty cycle)."""
        self.set_pwm(channel, 0, 0)

    def set_duty_cycle(self, channel, duty):
        """Set duty cycle as a fraction (0.0 to 1.0).

        Args:
            channel: PCA9685 channel (0-15).
            duty: Duty cycle fraction (0.0 = off, 1.0 = fully on).
        """
        duty = max(0.0, min(1.0, duty))
        if duty == 0.0:
            self.set_channel_full_off(channel)
        elif duty >= 1.0:
            self.set_channel_full_on(channel)
        else:
            off_val = int(duty * 4095)
            self.set_pwm(channel, 0, off_val)

    def cleanup(self):
        """Turn off all channels and close the I2C bus."""
        self.set_all_pwm(0, 0)
        self.bus.close()


class MotorDriver:
    """High-level interface for controlling two DC motors via TB6612FNG.

    Motor A is the left motor, Motor B is the right motor.
    Speed values range from -1.0 (full reverse) to 1.0 (full forward).
    """

    def __init__(self, pwm=None):
        """Initialize the motor driver.

        Args:
            pwm: Optional PCA9685 instance. If None, creates one.
        """
        if pwm is None:
            self.pwm = PCA9685()
        else:
            self.pwm = pwm

        from src.config import MOTOR_PWM_FREQ
        self.pwm.set_pwm_freq(MOTOR_PWM_FREQ)
        self.stop()
        logger.info("Motor driver initialized")

    def _set_motor(self, pwm_ch, in1_ch, in2_ch, ina_ch, inb_ch, speed, trim=1.0):
        """Control a single motor.

        The Waveshare JetBot drives direction via both Adafruit channels
        (in1/in2) and Waveshare low channels (ina/inb) simultaneously.

        Args:
            pwm_ch: PCA9685 channel for PWM speed (Adafruit: 8 or 13).
            in1_ch: Adafruit direction pin 1 (10 or 11).
            in2_ch: Adafruit direction pin 2 (9 or 12).
            ina_ch: Waveshare low direction channel A.
            inb_ch: Waveshare low direction channel B.
            speed: Speed from -1.0 (reverse) to 1.0 (forward).
            trim: Speed multiplier for calibration.
        """
        speed = max(-1.0, min(1.0, speed)) * trim
        pwm_val = int(abs(speed) * 4095)

        if abs(speed) < 0.01:
            # Stop: all direction pins low, PWM off
            self.pwm.set_channel_full_off(in1_ch)
            self.pwm.set_channel_full_off(in2_ch)
            self.pwm.set_channel_full_off(pwm_ch)
            self.pwm.set_pwm(ina_ch, 0, 0)
            self.pwm.set_pwm(inb_ch, 0, 0)
        elif speed > 0:
            # Forward: IN1=LOW, IN2=HIGH + INA=0, INB=speed
            self.pwm.set_channel_full_off(in1_ch)
            self.pwm.set_channel_full_on(in2_ch)
            self.pwm.set_duty_cycle(pwm_ch, abs(speed))
            self.pwm.set_pwm(ina_ch, 0, 0)
            self.pwm.set_pwm(inb_ch, 0, pwm_val)
        else:
            # Reverse: IN1=HIGH, IN2=LOW + INA=speed, INB=0
            self.pwm.set_channel_full_on(in1_ch)
            self.pwm.set_channel_full_off(in2_ch)
            self.pwm.set_duty_cycle(pwm_ch, abs(speed))
            self.pwm.set_pwm(ina_ch, 0, pwm_val)
            self.pwm.set_pwm(inb_ch, 0, 0)

    def set_left(self, speed):
        """Set left motor speed.

        Args:
            speed: -1.0 (reverse) to 1.0 (forward).
        """
        from src.config import MOTOR_A_TRIM
        self._set_motor(
            MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2,
            MOTOR_A_INA, MOTOR_A_INB, speed, MOTOR_A_TRIM,
        )

    def set_right(self, speed):
        """Set right motor speed.

        Args:
            speed: -1.0 (reverse) to 1.0 (forward).
        """
        from src.config import MOTOR_B_TRIM
        self._set_motor(
            MOTOR_B_PWM, MOTOR_B_IN1, MOTOR_B_IN2,
            MOTOR_B_INA, MOTOR_B_INB, speed, MOTOR_B_TRIM,
        )

    def set_motors(self, left_speed, right_speed):
        """Set both motors simultaneously.

        Args:
            left_speed: Left motor speed (-1.0 to 1.0).
            right_speed: Right motor speed (-1.0 to 1.0).
        """
        self.set_left(left_speed)
        self.set_right(right_speed)

    def stop(self):
        """Stop both motors immediately."""
        self.set_motors(0, 0)

    def cleanup(self):
        """Stop motors and release hardware resources."""
        self.stop()
        self.pwm.cleanup()
