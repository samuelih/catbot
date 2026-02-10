"""
CatToy configuration constants.

All hardware addresses, pin mappings, thresholds, and tuning parameters
are defined here. Change these values to calibrate your specific robot.
"""

# --- I2C ---
I2C_BUS = 1
PCA9685_ADDRESS = 0x60

# --- PCA9685 Registers ---
PCA9685_MODE1 = 0x00
PCA9685_MODE2 = 0x01
PCA9685_PRESCALE = 0xFE
PCA9685_LED0_ON_L = 0x06
PCA9685_LED0_ON_H = 0x07
PCA9685_LED0_OFF_L = 0x08
PCA9685_LED0_OFF_H = 0x09
PCA9685_ALL_LED_ON_L = 0xFA
PCA9685_ALL_LED_OFF_L = 0xFC

# MODE1 bits
PCA9685_RESTART = 0x80
PCA9685_SLEEP = 0x10
PCA9685_ALLCALL = 0x01

# MODE2 bits
PCA9685_OUTDRV = 0x04

# Internal oscillator frequency
PCA9685_OSC_FREQ = 25000000.0

# --- Motor PWM ---
MOTOR_PWM_FREQ = 1600  # Hz - Adafruit Motor HAT default

# --- TB6612FNG Channel Mapping (Waveshare JetBot) ---
# The Waveshare JetBot expansion board uses Adafruit Motor HAT-style wiring.
# PWM speed control is on channels 8/13 (Adafruit convention).
# Direction is driven on BOTH Adafruit channels (9-12) AND low channels (0-3).
#
# Motor A = Left Motor (Adafruit Motor 1)
MOTOR_A_PWM = 8    # Speed control (Adafruit ch8)
MOTOR_A_IN2 = 9    # Direction pin 2 (Adafruit ch9)
MOTOR_A_IN1 = 10   # Direction pin 1 (Adafruit ch10)
MOTOR_A_INA = 1    # Waveshare low direction channel
MOTOR_A_INB = 0    # Waveshare low direction channel

# Motor B = Right Motor (Adafruit Motor 2)
MOTOR_B_IN1 = 11   # Direction pin 1 (Adafruit ch11)
MOTOR_B_IN2 = 12   # Direction pin 2 (Adafruit ch12)
MOTOR_B_PWM = 13   # Speed control (Adafruit ch13)
MOTOR_B_INA = 2    # Waveshare low direction channel
MOTOR_B_INB = 3    # Waveshare low direction channel

# --- Motor Calibration ---
# Speed multiplier per motor (0.0 to 1.0)
# Adjust if one motor is faster than the other
MOTOR_A_TRIM = 1.0
MOTOR_B_TRIM = 1.0

# Maximum allowed speed (0.0 to 1.0)
# Limits top speed for safety during testing
MAX_SPEED = 0.8

# Minimum speed that actually moves the robot (below this, motors stall)
MIN_SPEED = 0.15

# --- Camera ---
CAMERA_CAPTURE_WIDTH = 1280
CAMERA_CAPTURE_HEIGHT = 720
CAMERA_DISPLAY_WIDTH = 300
CAMERA_DISPLAY_HEIGHT = 300
CAMERA_FRAMERATE = 30
CAMERA_FLIP_METHOD = 0  # 0=none, 2=180 degrees

# --- Cat Detection ---
DETECTION_MODEL = "ssd-mobilenet-v2"
DETECTION_THRESHOLD = 0.5  # confidence threshold

# COCO class IDs
# In jetson-inference, class descriptions are strings.
# "cat" in COCO is class ID 16 (0-indexed) / 17 (1-indexed)
CAT_CLASS_NAME = "cat"

# --- Collision Avoidance ---
# The bottom portion of the frame to analyze for obstacles
AVOIDANCE_ZONE_TOP_RATIO = 0.65  # Start analyzing from 65% down
AVOIDANCE_EDGE_THRESHOLD = 50    # Edge detection threshold (0-255)
AVOIDANCE_PIXEL_THRESHOLD = 0.3  # If >30% of avoidance zone has edges = obstacle
AVOIDANCE_COOLDOWN = 1.5         # Seconds to back up when avoiding

# --- State Machine ---
IDLE_DURATION = 3.0          # Seconds in IDLE before seeking
SEEKING_SPIN_DURATION = 2.0  # Seconds to spin in one direction
SEEKING_SPEED = 0.25         # Motor speed while seeking
CHASE_BASE_SPEED = 0.4      # Base speed while chasing
CHASE_MAX_SPEED = 0.7       # Max speed while chasing
CHASE_STEERING_GAIN = 0.8   # How aggressively to steer toward cat
CAT_LOST_TIMEOUT = 2.0      # Seconds without detection before giving up
AVOIDANCE_BACKUP_SPEED = 0.3  # Speed when backing up to avoid

# --- Gamepad ---
GAMEPAD_DEADZONE = 0.1  # Ignore stick values below this

# --- OLED Display ---
OLED_ADDRESS = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 32

# --- Battery Monitor ---
INA219_ADDRESS = 0x41
BATTERY_LOW_VOLTAGE = 9.6    # 3S LiPo low voltage cutoff (3.2V per cell)
BATTERY_FULL_VOLTAGE = 12.6  # 3S fully charged
