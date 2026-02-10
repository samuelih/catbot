# Hardware Reference

Detailed technical reference for every hardware component in the CatToy robot.

## 1. NVIDIA Jetson Nano 2GB Developer Kit

| Parameter | Value |
|-----------|-------|
| CPU | Quad-core ARM Cortex-A57 @ 1.43 GHz |
| GPU | 128-core NVIDIA Maxwell |
| RAM | 2GB LPDDR4 (shared CPU/GPU) |
| Storage | MicroSD (64GB in our kit) |
| USB | 1x USB 3.0, 2x USB 2.0 |
| Video out | HDMI |
| Camera | 1x MIPI CSI-2 connector |
| GPIO | 40-pin header (J6) |
| Network | Gigabit Ethernet (built-in), USB WiFi (add-on) |
| Power | 5V via USB-C or GPIO header |
| OS | JetPack 4.6.6 (Ubuntu 18.04, L4T R32.7.6, kernel 4.9.x-tegra) |

### JetPack 4.6.6 End-of-Life Notice

JetPack 4.6.6 is the FINAL release for the Jetson Nano platform. NVIDIA has ended support. The system will continue to work but will not receive security updates from NVIDIA. JetPack 5/6 does NOT support Jetson Nano (only Jetson Orin and newer).

### I2C Bus Details

The Jetson Nano 2GB has two I2C buses on the GPIO header:

| Bus | SDA Pin | SCL Pin | Used For |
|-----|---------|---------|----------|
| I2C Bus 1 | Pin 3 | Pin 5 | **JetBot expansion board** (motors, OLED, battery) |
| I2C Bus 0 | Pin 27 | Pin 28 | General purpose |

Access I2C bus 1 in Python:
```python
import smbus2
bus = smbus2.SMBus(1)  # Bus 1
```

### I2C Devices on Bus 1

| Address | Device | Function |
|---------|--------|----------|
| 0x3C | SSD1306 | 128x32 OLED display |
| 0x60 | PCA9685 | 16-channel PWM controller (motors) |
| 0x41 | INA219 | Battery voltage/current monitor |
| 0x70 | PCA9685 | ALL CALL broadcast address |

Verify with: `sudo i2cdetect -y -r 1`

---

## 2. JetBot Expansion Board

The expansion board sits on top of the Jetson Nano and provides:
- Motor control (PCA9685 + TB6612FNG)
- Battery management (3S 18650 holder + protection circuit)
- OLED display (SSD1306)
- Battery monitoring (INA219)
- Power regulation (APW7313 → 5V)

### PCA9685 PWM Controller

- I2C address: **0x60**
- 16 channels, 12-bit resolution (0-4095)
- Internal oscillator: 25 MHz
- PWM frequency range: 24 Hz - 1526 Hz
- Channels 0-5 are connected to the TB6612FNG motor driver

#### PCA9685 Register Map (Key Registers)

| Register | Address | Description |
|----------|---------|-------------|
| MODE1 | 0x00 | Mode register 1 (sleep, restart, auto-increment) |
| MODE2 | 0x01 | Mode register 2 (output driver config) |
| PRESCALE | 0xFE | PWM frequency prescaler |
| LED0_ON_L | 0x06 | Channel 0 ON low byte |
| LED0_ON_H | 0x07 | Channel 0 ON high byte |
| LED0_OFF_L | 0x08 | Channel 0 OFF low byte |
| LED0_OFF_H | 0x09 | Channel 0 OFF high byte |
| ALL_LED_ON_L | 0xFA | All channels ON low byte |
| ALL_LED_OFF_L | 0xFC | All channels OFF low byte |

Each subsequent channel adds 4 to the register address:
- Channel N ON_L = 0x06 + (4 * N)
- Channel N OFF_L = 0x08 + (4 * N)

#### Frequency Calculation

```
prescale = round(25000000 / (4096 * desired_freq)) - 1
```

For 100 Hz motor PWM: `prescale = round(25000000 / (4096 * 100)) - 1 = 60`

### TB6612FNG Motor Driver

The TB6612FNG is a dual H-bridge driver IC by Toshiba.

| Parameter | Value |
|-----------|-------|
| Motor voltage | 2.5V - 13.5V |
| Logic voltage | 2.7V - 5.5V |
| Continuous current per channel | 1.2A |
| Peak current per channel | 3.2A |
| Channels | 2 (Motor A and Motor B) |

#### PCA9685 Channel to TB6612FNG Pin Mapping

Based on the Waveshare Motor Driver HAT and jetbot_ros source code:

| PCA9685 Channel | TB6612FNG Pin | Function |
|-----------------|---------------|----------|
| 0 | PWMA | Motor A speed (PWM duty cycle) |
| 1 | AIN2 | Motor A direction pin 2 |
| 2 | AIN1 | Motor A direction pin 1 |
| 3 | BIN1 | Motor B direction pin 1 |
| 4 | BIN2 | Motor B direction pin 2 |
| 5 | PWMB | Motor B speed (PWM duty cycle) |

**Motor A = Left Motor, Motor B = Right Motor** (verify by testing - swap if your motors are reversed)

#### Motor Direction Control Truth Table

| AIN1/BIN1 | AIN2/BIN2 | PWMA/PWMB | Result |
|-----------|-----------|-----------|--------|
| LOW | HIGH | PWM | Forward (CW) |
| HIGH | LOW | PWM | Backward (CCW) |
| LOW | LOW | Any | Stop (coast) |
| HIGH | HIGH | Any | Brake (short) |

To drive Motor A forward at 50% speed:
```python
# Set direction: AIN1=LOW, AIN2=HIGH
pca9685.set_pwm(2, 0, 0)      # AIN1 = LOW (channel 2, off)
pca9685.set_pwm(1, 0, 4095)   # AIN2 = HIGH (channel 1, fully on)
# Set speed: 50% duty cycle
pca9685.set_pwm(0, 0, 2048)   # PWMA = 50% (channel 0)
```

---

## 3. IMX219-160 Camera

| Parameter | Value |
|-----------|-------|
| Sensor | Sony IMX219 |
| Resolution | 3280 x 2464 (8 megapixels) |
| CMOS Size | 1/4 inch |
| Aperture | F2.35 |
| Focal Length | 3.15 mm |
| FOV (diagonal) | 160 degrees |
| Interface | 15-pin MIPI CSI-2 ribbon cable |
| Max Framerate | 30 fps @ 1080p, 60 fps @ 720p |
| Device | `/dev/video0` |

### GStreamer Pipeline for Python/OpenCV

```python
def gstreamer_pipeline(
    capture_width=1280,
    capture_height=720,
    display_width=300,
    display_height=300,
    framerate=30,
    flip_method=0,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! appsink"
        % (
            capture_width, capture_height, framerate, flip_method,
            display_width, display_height,
        )
    )
```

**Pipeline element explanation:**
- `nvarguscamerasrc`: NVIDIA's hardware camera source for CSI cameras
- `video/x-raw(memory:NVMM)`: Tells GStreamer to use NVIDIA's zero-copy memory
- `nvvidconv`: Hardware-accelerated format/size conversion
- `flip-method`: 0=none, 1=CW90, 2=180, 3=CCW90, 4=h-flip, 5=v-flip
- `videoconvert`: Converts from BGRx to BGR (what OpenCV expects)
- `appsink`: Allows Python code to grab frames

---

## 4. Comfast CF-811AC V3 WiFi Adapter

| Parameter | Value |
|-----------|-------|
| Chipset | Realtek RTL8811CU |
| Interface | USB 2.0 |
| Bands | 2.4 GHz + 5 GHz (dual-band) |
| Max Speed | 150 Mbps (2.4G) + 433 Mbps (5G) |
| USB ID (WiFi mode) | `0bda:c811` |
| USB ID (CD-ROM mode) | `0bda:1a2b` |
| Kernel module | `8821cu` |
| Driver repo | https://github.com/ColdZoo/rtl8821cu-nvidia-jetson-nano |

---

## 5. DC Motors (JGB37-520)

| Parameter | Value |
|-----------|-------|
| Model | JGB37-520 |
| Nominal Voltage | 12V |
| Gear Ratio | 1:30 |
| No-Load Speed | ~333 RPM |
| No-Load Current | ~0.45A |
| Stall Current | ~2.8A |
| Encoder | Hall effect, 11 pulses/rev (330 after gearing) |

### Motor Wiring (6-pin connector)

| Wire Color | Function |
|------------|----------|
| Red | Motor power (+) |
| White | Motor power (-) |
| Blue | Encoder VCC (+) |
| Black | Encoder GND (-) |
| Yellow | Encoder signal A |
| Green | Encoder signal B |

Note: We use the motors without encoder feedback in this project. The encoder wires are not connected to the Jetson.

---

## 6. Power System

### Batteries
- 3x 18650 cells in series (3S configuration)
- Nominal: 11.1V (3 x 3.7V)
- Fully charged: 12.6V (3 x 4.2V)
- **Cells must be < 67mm length** (flat-top recommended)

### Protection Circuit
- S-8254AA + AO4407A: Over-charge, over-discharge, over-current, short-circuit protection

### Voltage Regulation
- APW7313: Steps battery voltage (11.1-12.6V) down to 5V for the Jetson Nano

### Battery Monitoring
- INA219 at I2C address 0x41: Reads voltage and current

### Power Flow

```
Batteries (11.1-12.6V)
    │
    ├─── Protection circuit (S-8254AA)
    │
    ├─── Direct to TB6612FNG (motor power)
    │
    └─── APW7313 (5V regulator)
             │
             ├─── Jetson Nano 2GB (5V, ~2-3A)
             ├─── PCA9685 logic
             ├─── OLED display
             ├─── INA219 monitor
             └─── 4010 cooling fan

Total typical power draw: 5V @ 2-3A = 10-15W
Battery capacity (typical 2600mAh cells): 11.1V × 2.6Ah = 28.9Wh
Expected runtime: ~2 hours
```

---

## 7. Wireless Gamepad

The kit includes a generic 2.4GHz USB wireless gamepad. It uses a USB dongle receiver.

- Interface: USB HID (Human Interface Device)
- Linux device: `/dev/input/eventX` or `/dev/input/js0`
- Python library: `evdev`
- Typical button mapping varies by manufacturer - the setup script includes a calibration tool

### Gamepad Input in Linux

```bash
# List input devices
ls /dev/input/

# See gamepad events in real-time
sudo evtest
# Select the gamepad device and press buttons to see event codes
```
