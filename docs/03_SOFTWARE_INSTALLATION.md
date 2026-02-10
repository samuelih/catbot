# Software Installation Guide

This guide walks you through installing all the CatToy software dependencies on your Jetson Nano.

## Prerequisites

Before starting, make sure you've completed [02_JETSON_NANO_SETUP.md](02_JETSON_NANO_SETUP.md):
- Jetson Nano is booted and accessible via SSH
- WiFi is working
- Camera is detected
- I2C devices are visible
- Swap space is configured

## Quick Install (Automated)

If you want to install everything at once:

```bash
cd ~/cattoy
sudo bash scripts/setup/install_dependencies.sh
```

This script does everything described below. Read on if you want to understand what each step does.

## Manual Installation Steps

### Step 1: Update the System

```bash
sudo apt update && sudo apt upgrade -y
```

**What this does:** Downloads the latest package lists (`update`) and installs any available updates (`upgrade`). The `-y` flag means "yes to all prompts."

### Step 2: Install System Dependencies

```bash
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    python3-numpy \
    i2c-tools \
    libgstreamer1.0-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    v4l-utils \
    cmake \
    libopencv-dev \
    python3-opencv
```

**What these are:**
- `python3-pip`: Python package installer (like an app store for Python libraries)
- `python3-dev`, `python3-setuptools`, `python3-wheel`: Tools for building Python packages
- `python3-numpy`: Math library (needed for image processing)
- `i2c-tools`: Utilities to communicate with I2C devices (motors, sensors)
- `libgstreamer1.0-dev`, `gstreamer1.0-*`: Video pipeline framework (for the camera)
- `v4l-utils`: Video4Linux utilities (camera diagnostics)
- `cmake`: Build tool (needed to compile jetson-inference)
- `libopencv-dev`, `python3-opencv`: Computer vision library

### Step 3: Install Python Libraries

```bash
pip3 install --user \
    smbus2 \
    evdev \
    pillow
```

**What these are:**
- `smbus2`: Python library to talk to I2C devices (motor controller, battery monitor)
- `evdev`: Python library to read gamepad/joystick input
- `pillow`: Python imaging library

### Step 4: Install NVIDIA jetson-inference

This is the key library for cat detection. It provides pre-trained AI models optimized for the Jetson's GPU.

```bash
# Clone the repository
mkdir -p ~/build
cd ~/build
git clone --recursive https://github.com/dusty-nv/jetson-inference.git
cd jetson-inference

# Create build directory
mkdir build
cd build
cmake ..
```

During the cmake step, a dialog will appear asking which models to download. Select:
- **SSD-Mobilenet-v2** (used for cat detection - it knows 90 object types including "cat")

Then:
```bash
# Compile (this takes 10-30 minutes on the Nano)
make -j$(nproc)

# Install
sudo make install
sudo ldconfig
```

**What this does:** Downloads, compiles, and installs NVIDIA's inference library with TensorRT optimization. The first time you run a detection, it will convert the model to a TensorRT engine file optimized for your specific GPU. This conversion takes several minutes but only happens once.

### Step 5: Install the CatToy Software

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/cattoy.git
cd cattoy
pip3 install --user -e .
```

Or if you've copied the code manually:
```bash
cd ~/cattoy
pip3 install --user -e .
```

The `-e` flag installs in "editable" mode - changes to the source code take effect immediately without reinstalling.

### Step 6: Verify Everything Works

Run the hardware diagnostics:

```bash
cd ~/cattoy
python3 scripts/diagnostics/check_hardware.py
```

This will check:
- Camera is accessible
- I2C bus is working
- PCA9685 motor controller responds
- Battery voltage is readable
- Gamepad is detected (if plugged in)

## COCO Dataset Cat Class

The SSD-MobileNet-V2 model is trained on the COCO dataset, which includes 90 object classes. The ones relevant to us:

| Class ID | Name |
|----------|------|
| 15 | cat |
| 16 | dog |
| 0 | person |

The `cat` class ID in the COCO dataset used by jetson-inference is **16** (0-indexed). Our software filters detections to only react to this class.

## File Locations After Installation

| What | Where |
|------|-------|
| CatToy source code | `~/cattoy/` |
| jetson-inference | `~/build/jetson-inference/` |
| TensorRT engine files | `~/build/jetson-inference/data/networks/` |
| Python packages | `~/.local/lib/python3.6/site-packages/` |
| WiFi driver source | `~/build/rtl8821cu-nvidia-jetson-nano/` |
| System Python | `/usr/bin/python3` |

## Troubleshooting

### "No module named 'jetson_inference'"
The jetson-inference library wasn't installed properly. Re-run:
```bash
cd ~/build/jetson-inference/build
sudo make install
sudo ldconfig
```

### "No module named 'smbus2'"
```bash
pip3 install --user smbus2
```

### "Permission denied" on I2C
Add your user to the i2c group:
```bash
sudo usermod -aG i2c $USER
# Then log out and back in
```

### Out of memory during jetson-inference build
Make sure swap is enabled:
```bash
free -h
# If swap shows 0, re-do the swap setup from the previous guide
```

Also try building with fewer parallel jobs:
```bash
make -j1  # Use only 1 core (slower but uses less RAM)
```
