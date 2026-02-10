#!/bin/bash
#
# CatToy - WiFi Driver Installation Script
#
# Installs the Realtek RTL8811CU driver for the Comfast CF-811AC V3
# USB WiFi adapter on Jetson Nano (JetPack 4.x, kernel 4.9.x-tegra).
#
# Run: sudo bash scripts/setup/install_wifi_driver.sh
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
    log_error "Please run with sudo: sudo bash $0"
    exit 1
fi

ACTUAL_USER="${SUDO_USER:-$USER}"
BUILD_DIR="/home/$ACTUAL_USER/build"

log_info "=== Comfast CF-811AC V3 (RTL8811CU) WiFi Driver Installer ==="
log_info ""
log_info "Adapter chipset: Realtek RTL8811CU"
log_info "USB ID (WiFi mode): 0bda:c811"
log_info "Kernel: $(uname -r)"
log_info ""

# Step 1: Install prerequisites
log_info "Step 1: Installing build prerequisites..."
apt update
apt install -y build-essential dkms git bc usb-modeswitch

# Step 2: Check current state
log_info "Step 2: Checking USB devices..."
if lsusb | grep -q "0bda:1a2b"; then
    log_warn "Adapter detected in CD-ROM mode (0bda:1a2b)."
    log_info "Switching to WiFi mode..."
    usb_modeswitch -KW -v 0bda -p 1a2b || true
    sleep 2
fi

if lsusb | grep -q "0bda:c811"; then
    log_info "Adapter detected in WiFi mode (0bda:c811). Good!"
elif lsusb | grep -q "0bda"; then
    log_warn "Realtek device detected but not in expected mode."
    log_warn "Continuing anyway..."
else
    log_warn "No Realtek USB device detected. Is the adapter plugged in?"
    log_warn "Continuing with driver installation anyway..."
fi

# Step 3: Clone the driver
log_info "Step 3: Downloading driver source..."
sudo -u "$ACTUAL_USER" mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

if [ -d "rtl8821cu-nvidia-jetson-nano" ]; then
    log_warn "Driver source already exists. Removing and re-cloning..."
    rm -rf rtl8821cu-nvidia-jetson-nano
fi

sudo -u "$ACTUAL_USER" git clone https://github.com/ColdZoo/rtl8821cu-nvidia-jetson-nano.git
cd rtl8821cu-nvidia-jetson-nano

# Step 4: Install via DKMS
log_info "Step 4: Building and installing driver via DKMS..."

if ./dkms-install.sh; then
    log_info "DKMS installation succeeded!"
else
    log_warn "DKMS installation failed. Trying manual build..."

    # Fix known ARM64 compilation issue
    MAKEFILE_PATH="/lib/modules/$(uname -r)/build/arch/arm64/Makefile"
    if [ -f "$MAKEFILE_PATH" ]; then
        if grep -q "mgeneral-regs-only" "$MAKEFILE_PATH"; then
            log_info "Fixing ARM64 Makefile (-mgeneral-regs-only)..."
            cp "$MAKEFILE_PATH" "${MAKEFILE_PATH}.backup"
            sed -i 's/-mgeneral-regs-only//' "$MAKEFILE_PATH"
        fi
    fi

    make clean || true
    make
    make install
    modprobe 8821cu || true
fi

# Step 5: Set up USB mode switch udev rule
log_info "Step 5: Configuring USB mode switch..."
UDEV_FILE="/lib/udev/rules.d/40-usb_modeswitch.rules"
RULE='ATTR{idVendor}=="0bda", ATTR{idProduct}=="1a2b", RUN+="/usr/sbin/usb_modeswitch -K -v 0bda -p 1a2b"'

if grep -q "0bda.*1a2b" "$UDEV_FILE" 2>/dev/null; then
    log_info "USB mode switch rule already exists."
else
    # Add rule before the LABEL line if it exists, otherwise append
    if grep -q "modeswitch_rules_end" "$UDEV_FILE" 2>/dev/null; then
        sed -i "/modeswitch_rules_end/i $RULE" "$UDEV_FILE"
    else
        echo "$RULE" >> "$UDEV_FILE"
    fi
    udevadm control --reload-rules
    log_info "USB mode switch udev rule added."
fi

# Step 6: Disable power management
log_info "Step 6: Disabling WiFi power management..."
echo "options 8821cu rtw_power_mgnt=0" > /etc/modprobe.d/8821cu.conf
log_info "Power management disabled."

# Step 7: Verify
log_info "Step 7: Verifying installation..."

if lsmod | grep -q 8821cu; then
    log_info "Driver module '8821cu' is loaded. SUCCESS!"
else
    log_warn "Driver module not loaded yet. It will load after reboot."
fi

echo ""
echo "============================================"
log_info "WiFi driver installation complete!"
echo "============================================"
echo ""
log_info "Please reboot now: sudo reboot"
echo ""
log_info "After reboot, connect to WiFi:"
echo "  sudo nmcli device wifi list"
echo "  sudo nmcli device wifi connect \"YOUR_WIFI_NAME\" password \"YOUR_PASSWORD\""
echo ""
log_info "Verify connection:"
echo "  ping -c 3 google.com"
