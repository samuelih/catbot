"""
CatToy state machine controller.

Orchestrates the robot's behavior through distinct states:
IDLE -> SEEKING -> CHASING -> AVOIDING, with MANUAL override.
"""

import enum
import time

from src.config import (
    CAT_LOST_TIMEOUT,
    IDLE_DURATION,
    SEEKING_SPEED,
    SEEKING_SPIN_DURATION,
)
from src.utils.logger import setup_logger

logger = setup_logger("control.state_machine")


class State(enum.Enum):
    """Robot behavioral states."""
    IDLE = "IDLE"
    SEEKING = "SEEKING"
    CHASING = "CHASING"
    AVOIDING = "AVOIDING"
    MANUAL = "MANUAL"


class StateMachine:
    """Manages state transitions and tracks timing for the CatToy robot.

    This class only manages state logic. It does NOT directly control
    hardware - the main loop reads the current state and acts accordingly.
    """

    def __init__(self):
        self.state = State.IDLE
        self._state_start_time = time.time()
        self._last_cat_seen_time = 0
        self._seeking_direction = 1  # 1=right, -1=left
        self._last_spin_change = time.time()
        self._manual_requested = False

    @property
    def time_in_state(self):
        """Seconds spent in the current state."""
        return time.time() - self._state_start_time

    def _change_state(self, new_state):
        """Transition to a new state."""
        if new_state != self.state:
            logger.info(
                "State: %s -> %s (was in %s for %.1fs)",
                self.state.value,
                new_state.value,
                self.state.value,
                self.time_in_state,
            )
            self.state = new_state
            self._state_start_time = time.time()

    def request_manual(self):
        """Request transition to manual mode (from gamepad)."""
        self._manual_requested = True

    def exit_manual(self):
        """Exit manual mode back to idle."""
        self._manual_requested = False
        self._change_state(State.IDLE)

    def update(self, cat_detected, obstacle_detected, gamepad_active):
        """Update the state machine based on sensor inputs.

        Call this once per frame in the main loop.

        Args:
            cat_detected: True if a cat was detected in the current frame.
            obstacle_detected: True if an obstacle is dangerously close.
            gamepad_active: True if the gamepad has significant input.

        Returns:
            The current State after processing.
        """
        now = time.time()

        if cat_detected:
            self._last_cat_seen_time = now

        # Manual mode overrides everything
        if gamepad_active or self._manual_requested:
            if self.state != State.MANUAL:
                self._change_state(State.MANUAL)
            return self.state

        # If we were in manual and gamepad is released, go to idle
        if self.state == State.MANUAL and not gamepad_active:
            self._manual_requested = False
            self._change_state(State.IDLE)
            return self.state

        # Obstacle avoidance overrides everything except manual
        if obstacle_detected and self.state not in (State.MANUAL, State.AVOIDING):
            self._change_state(State.AVOIDING)
            return self.state

        # State-specific transitions
        if self.state == State.IDLE:
            if self.time_in_state > IDLE_DURATION:
                self._change_state(State.SEEKING)

        elif self.state == State.SEEKING:
            if cat_detected:
                self._change_state(State.CHASING)

            # Alternate spin direction
            if now - self._last_spin_change > SEEKING_SPIN_DURATION:
                self._seeking_direction *= -1
                self._last_spin_change = now

        elif self.state == State.CHASING:
            if obstacle_detected:
                self._change_state(State.AVOIDING)
            elif now - self._last_cat_seen_time > CAT_LOST_TIMEOUT:
                logger.info("Cat lost for %.1fs, switching to SEEKING",
                            CAT_LOST_TIMEOUT)
                self._change_state(State.SEEKING)

        elif self.state == State.AVOIDING:
            # Return to seeking after avoidance maneuver
            if self.time_in_state > 2.0:
                self._change_state(State.SEEKING)

        return self.state

    @property
    def seeking_direction(self):
        """Current seeking spin direction: 1=right, -1=left."""
        return self._seeking_direction
