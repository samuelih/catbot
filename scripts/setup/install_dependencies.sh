#!/bin/bash
#
# CatToy - Complete Dependency Installation Script
#
# Run this on your Jetson Nano 2GB after flashing JetPack 4.6.x:
#   sudo bash scripts/setup/install_dependencies.sh
#
# This script:
#   1. Updates the system
#   2. Installs system packages (compilers, I2C tools, GStreamer, OpenCV)
#   3. Installs Python packages (smbus2, evdev, pillow)
#   4. Installs NVIDIA jetson-inference (AI detection library)
#   5. Sets up swap space (needed for 2GB RAM limit)
#   6. Configures system settings for robotics use
#

set -e  # Exit on any error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check we're running on Jetson
if [ ! -f /etc/nv_tegra_release ]; then
    log_error "This script must be run on an NVIDIA Jetson device."
    log_error "File /etc/nv_tegra_release not found."
    exit 1
fi

# Check we're running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run with sudo: sudo bash $0"
    exit 1
fi

ACTUAL_USER="${SUDO_USER:-$USER}"
log_info "Installing as user: $ACTUAL_USER"

# ============================================================
# Step 1: System Update
# ============================================================
log_info "Step 1/6: Updating system packages..."
apt update
apt upgrade -y

# ============================================================
# Step 2: System Dependencies
# ============================================================
log_info "Step 2/6: Installing system dependencies..."
apt install -y \
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
    build-essential \
    git \
    bc \
    libopencv-dev \
    python3-opencv \
    usb-modeswitch

# ============================================================
# Step 3: Python Dependencies
# ============================================================
log_info "Step 3/6: Installing Python packages..."
sudo -u "$ACTUAL_USER" pip3 install --user \
    smbus2 \
    evdev \
    pillow \
    pytest

# ============================================================
# Step 4: Swap Space
# ============================================================
log_info "Step 4/6: Setting up swap space..."
if [ -f /swapfile ]; then
    log_warn "Swap file already exists, skipping."
else
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    # Add to fstab if not already there
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    log_info "4GB swap file created and enabled."
fi

# ============================================================
# Step 5: System Configuration
# ============================================================
log_info "Step 5/6: Configuring system..."

# Add user to I2C and GPIO groups
usermod -aG i2c "$ACTUAL_USER" 2>/dev/null || true
usermod -aG gpio "$ACTUAL_USER" 2>/dev/null || true

# Set max performance mode
nvpmodel -m 0 2>/dev/null || log_warn "Could not set nvpmodel"
jetson_clocks 2>/dev/null || log_warn "Could not set jetson_clocks"

# Create udev rule for gamepad permissions
cat > /etc/udev/rules.d/99-input.rules << 'EOF'
# Allow non-root access to input devices (gamepad)
KERNEL=="event[0-9]*", SUBSYSTEM=="input", MODE="0666"
KERNEL=="js[0-9]*", SUBSYSTEM=="input", MODE="0666"
EOF
udevadm control --reload-rules

log_info "User added to i2c and gpio groups."
log_info "Performance mode set to maximum."

# ============================================================
# Step 6: NVIDIA jetson-inference
# ============================================================
log_info "Step 6/6: Installing NVIDIA jetson-inference..."
log_info "This step compiles from source and may take 20-40 minutes."

BUILD_DIR="/home/$ACTUAL_USER/build"
sudo -u "$ACTUAL_USER" mkdir -p "$BUILD_DIR"

if [ -d "$BUILD_DIR/jetson-inference" ]; then
    log_warn "jetson-inference directory already exists. Skipping clone."
else
    cd "$BUILD_DIR"
    sudo -u "$ACTUAL_USER" git clone --recursive https://github.com/dusty-nv/jetson-inference.git
fi

cd "$BUILD_DIR/jetson-inference"
sudo -u "$ACTUAL_USER" mkdir -p build
cd build

# Run cmake (will show model download dialog)
log_info "Running cmake... A dialog may appear to select models."
log_info "Select 'SSD-Mobilenet-v2' when prompted."
cmake ..

# Compile
log_info "Compiling jetson-inference (this takes a while)..."
make -j$(nproc)

# Install
make install
ldconfig

log_info "jetson-inference installed successfully."

# ============================================================
# Done
# ============================================================
echo ""
echo "============================================"
log_info "Installation complete!"
echo "============================================"
echo ""
log_info "Next steps:"
echo "  1. Reboot: sudo reboot"
echo "  2. After reboot, test hardware: python3 ~/cattoy/scripts/diagnostics/check_hardware.py"
echo "  3. Run the cat toy: cd ~/cattoy && python3 src/main.py"
echo ""
log_warn "Remember to reboot for group membership changes to take effect."
