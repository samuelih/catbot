#!/usr/bin/env python3
"""
CatToy - Autonomous Cat Toy Robot

Main entry point. Runs the state machine loop that:
1. Captures camera frames
2. Detects cats using AI (SSD-MobileNet-V2 via TensorRT)
3. Avoids obstacles using edge detection
4. Controls motors to chase the cat or respond to gamepad input

Usage:
    python3 src/main.py                    # Autonomous mode
    python3 src/main.py --mode manual      # Gamepad-only mode
    python3 src/main.py --debug            # Verbose logging
    python3 src/main.py --threshold 0.4    # Lower detection threshold
    python3 src/main.py --speed 0.3        # Limit max speed
"""

import argparse
import signal
import sys
import time

from src.camera.capture import Camera
from src.camera.detector import CatDetector
from src.avoidance.collision import CollisionDetector
from src.control.gamepad import Gamepad
from src.control.state_machine import State, StateMachine
from src.motor.movement import MovementController
from src.utils.logger import setup_logger


def parse_args():
    parser = argparse.ArgumentParser(description="CatToy - Autonomous Cat Toy Robot")
    parser.add_argument(
        "--mode",
        choices=["auto", "manual"],
        default="auto",
        help="Operating mode (default: auto)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Cat detection confidence threshold (default: 0.5)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=None,
        help="Maximum motor speed 0.0-1.0 (default: from config)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--no-avoidance",
        action="store_true",
        help="Disable collision avoidance (testing only)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logger("cattoy", debug=args.debug)

    # Override config values from CLI
    if args.speed is not None:
        import src.config as config
        config.MAX_SPEED = args.speed
        config.CHASE_MAX_SPEED = min(config.CHASE_MAX_SPEED, args.speed)

    logger.info("=== CatToy Starting ===")
    logger.info("Mode: %s | Threshold: %.2f | Avoidance: %s",
                args.mode, args.threshold,
                "OFF" if args.no_avoidance else "ON")

    # Initialize subsystems
    logger.info("Initializing camera...")
    camera = Camera(use_jetson_utils=True)

    logger.info("Initializing cat detector (model loading may take minutes)...")
    detector = CatDetector(threshold=args.threshold)

    logger.info("Initializing collision detector...")
    collision = CollisionDetector()

    logger.info("Initializing motors...")
    movement = MovementController()

    logger.info("Initializing gamepad...")
    gamepad = Gamepad()
    gamepad.start()

    state_machine = StateMachine()

    # If manual mode requested, start in manual
    if args.mode == "manual":
        state_machine.request_manual()

    # Graceful shutdown handler
    running = True

    def shutdown(sig, frame):
        nonlocal running
        logger.info("Shutdown signal received")
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # FPS tracking
    frame_count = 0
    fps_start_time = time.time()
    current_fps = 0.0

    logger.info("=== Main loop starting ===")

    try:
        while running:
            loop_start = time.time()

            # 1. Capture frame
            image = camera.capture()
            if image is None:
                time.sleep(0.01)
                continue

            # 2. Detect cats
            cat_detections = detector.detect(image)
            cat_detected = len(cat_detections) > 0

            # Get the largest/closest cat detection
            best_cat = None
            if cat_detected:
                best_cat = max(cat_detections, key=lambda d: d.area)

            # 3. Check for obstacles
            obstacle_detected = False
            if not args.no_avoidance:
                obstacle_detected, edge_density = collision.check_obstacle(image)

            # 4. Check gamepad
            gamepad_active = gamepad.has_input()

            # Handle gamepad button_b as emergency stop
            if gamepad.state.button_b:
                movement.stop()
                continue

            # Handle gamepad button_a to toggle manual/auto
            if gamepad.state.button_a:
                if state_machine.state == State.MANUAL:
                    state_machine.exit_manual()
                else:
                    state_machine.request_manual()
                time.sleep(0.3)  # Debounce

            # Handle HOME button to exit manual
            if gamepad.state.button_home:
                state_machine.exit_manual()
                time.sleep(0.3)

            # 5. Update state machine
            state = state_machine.update(
                cat_detected=cat_detected,
                obstacle_detected=obstacle_detected,
                gamepad_active=gamepad_active,
            )

            # 6. Act based on current state
            if state == State.IDLE:
                movement.stop()

            elif state == State.SEEKING:
                if state_machine.seeking_direction > 0:
                    movement.spin_right()
                else:
                    movement.spin_left()

            elif state == State.CHASING:
                if best_cat is not None:
                    movement.chase_target(
                        target_x_normalized=best_cat.center_x_normalized,
                        target_size_normalized=best_cat.size_normalized,
                    )
                else:
                    # Cat was detected but we lost tracking - slow down
                    movement.forward(0.2)

            elif state == State.AVOIDING:
                movement.avoid_obstacle()
                # avoid_obstacle is blocking (takes ~1.5s), then we continue

            elif state == State.MANUAL:
                # Convert gamepad input to differential drive
                forward = -gamepad.state.left_y  # Negate: stick up = forward
                turn = gamepad.state.left_x
                left_speed = forward + turn
                right_speed = forward - turn
                movement.motors.set_motors(
                    max(-1.0, min(1.0, left_speed)),
                    max(-1.0, min(1.0, right_speed)),
                )

            # FPS tracking
            frame_count += 1
            elapsed = time.time() - fps_start_time
            if elapsed >= 2.0:
                current_fps = frame_count / elapsed
                frame_count = 0
                fps_start_time = time.time()

                # Periodic status log
                detection_fps = detector.get_fps()
                logger.info(
                    "State: %s | FPS: %.1f | Detection FPS: %.1f | Cat: %s",
                    state.value,
                    current_fps,
                    detection_fps,
                    f"YES (conf={best_cat.confidence:.2f})" if best_cat else "no",
                )

    except Exception as e:
        logger.error("Fatal error in main loop: %s", e, exc_info=True)
    finally:
        logger.info("Shutting down...")
        movement.cleanup()
        camera.close()
        gamepad.stop()
        logger.info("=== CatToy stopped ===")


if __name__ == "__main__":
    main()
