# CatToy Usage Guide

## Running the Robot

### Basic Usage

```bash
cd ~/cattoy

# Run in autonomous mode (default)
python3 src/main.py

# Run in manual-only mode (gamepad control)
python3 src/main.py --mode manual

# Run with debug logging
python3 src/main.py --debug

# Run with custom detection confidence threshold
python3 src/main.py --threshold 0.4
```

### Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--mode` | `auto` | `auto` = autonomous cat chasing, `manual` = gamepad only |
| `--threshold` | `0.5` | Cat detection confidence threshold (0.0-1.0). Lower = more sensitive but more false positives |
| `--speed` | `0.5` | Maximum motor speed (0.0-1.0). Start low when testing! |
| `--debug` | off | Enable verbose logging |
| `--no-avoidance` | off | Disable collision avoidance (DANGEROUS - use for testing only) |

### Stopping the Robot

- **From SSH:** Press `Ctrl+C` in the terminal
- **From gamepad:** Press the HOME/MODE button (stops motors immediately)
- **Emergency:** Flip the power switch on the expansion board

## How It Works

### State Machine

The robot runs a continuous loop (~10-15 times per second):

1. **Capture** a camera frame
2. **Detect** objects in the frame using AI
3. **Check** for obstacles (collision avoidance)
4. **Decide** what to do based on the current state
5. **Act** by sending motor commands

### States

**IDLE** (startup state)
- Motors are stopped
- Camera is running and processing
- Transitions to SEEKING after 3 seconds

**SEEKING**
- Robot slowly spins in place, looking for a cat
- Alternates direction every few seconds
- Transitions to CHASING when a cat is detected

**CHASING**
- Robot moves toward the detected cat
- Uses proportional steering (turns harder when cat is off-center)
- Randomizes speed and adds zigzag patterns to be more interesting to the cat
- Transitions to AVOIDING if an obstacle is too close
- Transitions to SEEKING if cat is lost for >2 seconds

**AVOIDING**
- Robot stops, backs up, and turns away from the obstacle
- Transitions back to SEEKING after clearing the obstacle

**MANUAL**
- Entered when gamepad input is detected
- Full joystick/button control of the robot
- Transitions back to IDLE when gamepad HOME button is pressed

### Cat Detection

The AI model (SSD-MobileNet-V2) processes each camera frame and outputs bounding boxes around detected objects. We filter for class "cat" only.

Each detection provides:
- **Bounding box** (x1, y1, x2, y2) - where the cat is in the frame
- **Confidence** (0.0 to 1.0) - how sure the model is
- **Class ID** - what the object is (we only care about "cat")

The cat's position in the frame determines how the robot steers:
- Cat on the left → turn left
- Cat in the center → go straight
- Cat on the right → turn right
- Cat is large (close) → slow down
- Cat is small (far) → speed up

### Collision Avoidance

The collision avoidance system uses the lower portion of the camera frame to detect obstacles. It analyzes pixel density/edges in the bottom third of the frame:

- If the bottom of the frame has lots of detail/edges → something is close
- Triggers at ~30cm distance from obstacles
- Always overrides chasing behavior

## Gamepad Controls

| Input | Action |
|-------|--------|
| Left stick | Forward/backward + steering |
| Right stick | Rotate in place |
| A button | Toggle between manual and auto mode |
| B button | Emergency stop (all motors off) |
| HOME/MODE | Return to autonomous mode |

Note: Button mappings may vary by gamepad model. Run `scripts/diagnostics/test_gamepad.py` to see your specific button codes.

## Tips for Playing with Your Cat

1. **Start slow** - Use `--speed 0.3` at first. Cats startle easily.
2. **Open space** - Use in a room with space to move. Clear fragile items.
3. **Lighting** - The camera needs reasonable light. Dim rooms reduce detection accuracy.
4. **Cat mood** - Not all cats care about robots. Some love it, some ignore it. Try different speeds.
5. **Supervision** - Always watch the robot. The collision avoidance is good but not perfect.
6. **Battery** - The robot gets slower as batteries drain. Recharge when behavior becomes sluggish.

## Monitoring

While the robot runs, it outputs status information:

```
[INFO] State: SEEKING | FPS: 12.3 | Battery: 11.8V
[INFO] Cat detected! Confidence: 0.87 | Position: center-right
[INFO] State: CHASING | Speed: 0.45 | Steering: -0.2
[INFO] OBSTACLE DETECTED - switching to AVOIDING
```

To see the OLED display status:
- Line 1: IP address
- Line 2: State (IDLE/SEEKING/CHASING/etc)
- Line 3: Battery voltage
- Line 4: FPS

## Troubleshooting

### Robot doesn't move
1. Check batteries are charged (`python3 scripts/diagnostics/check_hardware.py`)
2. Verify I2C: `sudo i2cdetect -y -r 1` (should show 0x60)
3. Test motors directly: `python3 scripts/diagnostics/test_motors.py`

### Camera shows black/no detection
1. Check ribbon cable connection (blue side toward HDMI)
2. Test camera: `python3 scripts/diagnostics/test_camera.py`
3. Ensure you're not blocking the lens

### Poor cat detection
1. Ensure good lighting
2. Try lower threshold: `--threshold 0.3`
3. Make sure the cat is within ~3 meters
4. The model works best on house cats in typical indoor settings

### Robot crashes into things
1. Ensure collision avoidance is enabled (no `--no-avoidance` flag)
2. Camera must be forward-facing and not tilted up
3. Transparent objects (glass doors) are not detected - keep the robot away from them

### WiFi disconnects
1. Check signal strength: `iwconfig wlan0`
2. Disable power save: `sudo iw dev wlan0 set power_save off`
3. Stay within WiFi range when monitoring via SSH
