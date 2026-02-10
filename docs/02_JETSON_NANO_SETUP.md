# Jetson Nano 2GB - Complete Setup Guide

This guide assumes you know nothing about Linux. Every step is explained.

## Table of Contents

1. [What Is the Jetson Nano?](#what-is-the-jetson-nano)
2. [Flash the SD Card](#flash-the-sd-card)
3. [First Boot](#first-boot)
4. [Basic Linux Concepts](#basic-linux-concepts)
5. [Connect via SSH](#connect-via-ssh)
6. [Install WiFi Driver](#install-wifi-driver)
7. [System Configuration](#system-configuration)
8. [Add Swap Space](#add-swap-space)

---

## What Is the Jetson Nano?

The Jetson Nano 2GB is a small computer (about the size of a credit card) made by NVIDIA. It runs Linux (Ubuntu 18.04) and has a GPU (graphics processor) that can run AI models. Think of it as a more powerful Raspberry Pi that can do machine learning.

**Key specs:**
- CPU: Quad-core ARM Cortex-A57 @ 1.43 GHz
- GPU: 128-core NVIDIA Maxwell
- RAM: 2GB LPDDR4 (shared between CPU and GPU)
- Storage: MicroSD card (your 64GB card)
- OS: Ubuntu 18.04 (JetPack 4.6.x)

## Flash the SD Card

"Flashing" means writing the operating system onto the SD card.

### Step 1: Download the OS Image

Go to: https://developer.nvidia.com/embedded/jetpack-sdk-46

Download the **SD Card Image** for "Jetson Nano 2GB Developer Kit". The file is about 6GB.

The file will be named something like: `jetson-nano-2gb-jp46-sd-card-image.zip`

### Step 2: Download Etcher

Etcher is a program that writes the OS image to the SD card.

Download from: https://www.balena.io/etcher/

Install it on your computer (works on Windows, Mac, or Linux).

### Step 3: Flash

1. Insert the 64GB micro SD card into your computer using the SD card reader
2. Open Etcher
3. Click "Flash from file" and select the downloaded `.zip` file
4. Click "Select target" and choose your SD card (BE CAREFUL - pick the right drive!)
5. Click "Flash!" and wait (~10 minutes)
6. When done, remove the SD card

## First Boot

### Step 1: Assemble the Hardware

Before powering on, make sure:
- The JetBot expansion board is connected to the Jetson Nano's 40-pin header
- The IMX219-160 camera ribbon cable is connected to the CSI port (the small connector next to the HDMI port). The blue side of the ribbon faces the HDMI port.
- The cooling fan is connected to the fan header on the expansion board
- 3x 18650 batteries are inserted into the battery holder

**Do NOT plug in the WiFi adapter yet.** We'll set it up later.

### Step 2: Connect Peripherals (Headed Setup)

Connect to the Jetson Nano:
- HDMI cable to a monitor
- USB keyboard
- USB mouse
- Ethernet cable to your router (for internet access)

### Step 3: Power On

Flip the power switch on the expansion board. The green LED on the Jetson Nano should light up. The first boot takes several minutes.

### Step 4: Initial Setup Wizard

You'll see an Ubuntu setup wizard:
1. Accept the NVIDIA license agreement
2. Choose your language (English)
3. Choose your keyboard layout
4. Choose your timezone
5. Create a user account:
   - **Name:** catbot (or whatever you want)
   - **Computer name:** cattoy
   - **Username:** catbot
   - **Password:** choose something you'll remember
   - Check "Log in automatically"
6. Choose "Default" APP partition size
7. Wait for setup to complete (~5 minutes)

### Step 5: Open a Terminal

After the desktop loads:
1. Right-click on the desktop
2. Click "Open Terminal" (or press `Ctrl+Alt+T`)

This opens a **terminal** - a text-based interface where you type commands. This is how we'll do most of our work.

## Basic Linux Concepts

Here are the essential Linux concepts you need:

### The Terminal
- The terminal is where you type commands
- Each command does something specific
- After typing a command, press `Enter` to run it
- The `$` symbol means the terminal is ready for your next command

### Common Commands

```bash
# Show what directory you're in (pwd = "print working directory")
pwd

# List files in the current directory
ls

# Change directory (cd = "change directory")
cd /home/catbot

# Go to your home directory
cd ~

# Create a directory
mkdir my_folder

# Copy a file
cp file1.txt file2.txt

# Move/rename a file
mv old_name.txt new_name.txt

# Delete a file (BE CAREFUL - no undo!)
rm file.txt

# Show contents of a file
cat file.txt

# Edit a file with nano (a simple text editor)
nano file.txt
# (Ctrl+O to save, Ctrl+X to exit)

# Run a command as administrator (sudo = "superuser do")
sudo apt update

# Install software
sudo apt install package_name

# Check if something is running
ps aux | grep program_name

# Stop a running program
Ctrl+C
```

### File Paths
- `/` is the root (top) of the filesystem
- `/home/catbot/` is your home directory
- `~` is a shortcut for your home directory
- `.` means "current directory"
- `..` means "parent directory" (one level up)

### Permissions
- `sudo` runs a command as "root" (administrator)
- You'll need `sudo` for installing software and changing system settings
- It will ask for your password the first time

## Connect via SSH

SSH lets you control the Jetson Nano from another computer over the network. This is important because the robot won't have a monitor attached when it's running.

### Step 1: Find the Jetson's IP Address

On the Jetson Nano terminal, type:
```bash
hostname -I
```

This shows the IP address (something like `192.168.1.42`). Write it down.

### Step 2: SSH From Your Computer

**On Mac/Linux**, open Terminal and type:
```bash
ssh catbot@192.168.1.42
```
(Replace `192.168.1.42` with your actual IP address)

**On Windows**, use PuTTY (download from https://www.putty.org/) or Windows Terminal:
```
ssh catbot@192.168.1.42
```

Type `yes` when asked about the fingerprint, then enter your password.

You're now controlling the Jetson Nano remotely!

## Install WiFi Driver

The Comfast CF-811AC V3 USB WiFi adapter uses the Realtek RTL8811CU chipset, which does NOT have a built-in Linux driver. We need to compile one from source.

**This is why you need the Ethernet cable first** - you need internet access to download the driver.

### Step 1: Plug in the WiFi Adapter

Insert the CF-811AC V3 into a USB port on the Jetson Nano.

### Step 2: Verify It's Detected

```bash
lsusb
```

You should see a line containing `0bda:c811` or `Realtek Semiconductor`. If you see `0bda:1a2b` instead, the adapter is in CD-ROM mode and needs mode switching (see troubleshooting below).

### Step 3: Install Build Tools

```bash
sudo apt update
sudo apt install -y build-essential dkms git bc
```

**What these are:**
- `build-essential`: Compiler tools (gcc, make) needed to compile the driver
- `dkms`: Dynamic Kernel Module Support - makes the driver survive system updates
- `git`: Version control tool to download the driver source code
- `bc`: Calculator program needed by the build process

### Step 4: Download and Install the Driver

We use the ColdZoo fork which is pre-configured for Jetson Nano:

```bash
mkdir -p ~/build
cd ~/build
git clone https://github.com/ColdZoo/rtl8821cu-nvidia-jetson-nano.git
cd rtl8821cu-nvidia-jetson-nano
sudo ./dkms-install.sh
```

If the DKMS install fails, try the manual method:
```bash
# Fix a known ARM64 compilation issue
sudo sed -i 's/-mgeneral-regs-only//' /lib/modules/$(uname -r)/build/arch/arm64/Makefile

# Build manually
make
sudo make install
sudo modprobe 8821cu
```

### Step 5: Reboot

```bash
sudo reboot
```

### Step 6: Verify WiFi Works

After reboot, check that a wireless interface exists:
```bash
iwconfig
```

You should see `wlan0` or similar. If not, see troubleshooting.

### Step 7: Connect to WiFi

```bash
# List available networks
sudo nmcli device wifi list

# Connect to your network
sudo nmcli device wifi connect "YOUR_WIFI_NAME" password "YOUR_WIFI_PASSWORD"

# Verify connection
ping -c 3 google.com
```

### Step 8: Note Your WiFi IP

```bash
hostname -I
```

You'll now see two IP addresses - the Ethernet one and the WiFi one. You can disconnect the Ethernet cable and SSH over WiFi from now on.

### Troubleshooting: USB Mode Switching

If `lsusb` shows `0bda:1a2b` instead of `0bda:c811`:

```bash
sudo apt install -y usb-modeswitch
sudo usb_modeswitch -KW -v 0bda -p 1a2b
```

Make it permanent:
```bash
sudo bash -c 'cat >> /lib/udev/rules.d/40-usb_modeswitch.rules << EOF
# Realtek RTL8811CU WiFi mode switch
ATTR{idVendor}=="0bda", ATTR{idProduct}=="1a2b", RUN+="/usr/sbin/usb_modeswitch -K -v 0bda -p 1a2b"
EOF'
```

### Troubleshooting: WiFi Keeps Dropping

Disable power management:
```bash
sudo iw dev wlan0 set power_save off

# Make it permanent
sudo bash -c 'echo "options 8821cu rtw_power_mgnt=0" > /etc/modprobe.d/8821cu.conf'
```

## System Configuration

### Set Maximum Performance Mode

The Jetson Nano has different power modes. For our robot, we want maximum performance:

```bash
# Set to max performance (10W 4-core mode)
sudo nvpmodel -m 0

# Boost CPU/GPU clocks
sudo jetson_clocks
```

### Disable the Desktop GUI (Saves ~300MB RAM)

Since we'll control the robot via SSH, we don't need the graphical desktop:

```bash
# Disable GUI on boot (saves significant RAM on the 2GB model)
sudo systemctl set-default multi-user.target

# To re-enable later if needed:
# sudo systemctl set-default graphical.target
```

Reboot for this to take effect.

### Verify Camera

```bash
# Check if the camera is detected
ls /dev/video*
# Should show /dev/video0

# Quick camera test (will fail without display, but confirms driver works)
gst-launch-1.0 nvarguscamerasrc sensor-id=0 num-buffers=1 ! \
  'video/x-raw(memory:NVMM), width=1280, height=720' ! fakesink

# If this shows no errors, the camera is working
```

### Verify I2C Devices

```bash
# Install I2C tools
sudo apt install -y i2c-tools

# Scan I2C bus 1 (where the JetBot expansion board is)
sudo i2cdetect -y -r 1
```

You should see devices at these addresses:
- `0x3c` = OLED display (SSD1306)
- `0x40` = PWM controller (PCA9685)
- `0x41` = Battery monitor (INA219)
- `0x70` = PCA9685 ALL CALL address

If you don't see `0x40`, the expansion board is not properly connected.

## Add Swap Space

The Jetson Nano 2GB has very limited RAM. When running the AI model, it uses almost all of it. Swap space uses the SD card as extra "slow RAM" to prevent out-of-memory crashes.

```bash
# Create a 4GB swap file
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make it permanent (survives reboot)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify
free -h
# Should show ~4GB swap
```

**Note:** Swap is much slower than real RAM. The robot may briefly stutter when swap is being used. This is normal on the 2GB model.

## Next Steps

Once you've completed all the above:
1. You can SSH into the Jetson Nano over WiFi
2. The camera works
3. The I2C bus shows the expansion board devices
4. You have swap space configured

Continue to [03_SOFTWARE_INSTALLATION.md](03_SOFTWARE_INSTALLATION.md) to install the CatToy software.
