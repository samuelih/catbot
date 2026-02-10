"""Tests for the state machine."""

import time
import pytest
from unittest.mock import patch

from src.control.state_machine import State, StateMachine


@pytest.fixture
def sm():
    """Create a fresh StateMachine."""
    return StateMachine()


class TestStateMachine:
    def test_starts_in_idle(self, sm):
        assert sm.state == State.IDLE

    def test_idle_to_seeking_after_timeout(self, sm):
        with patch("src.control.state_machine.IDLE_DURATION", 0.0):
            sm.update(cat_detected=False, obstacle_detected=False,
                      gamepad_active=False)
            # After IDLE_DURATION expires, should transition
            assert sm.state == State.SEEKING

    def test_seeking_to_chasing_on_cat(self, sm):
        sm._change_state(State.SEEKING)
        sm.update(cat_detected=True, obstacle_detected=False,
                  gamepad_active=False)
        assert sm.state == State.CHASING

    def test_chasing_to_avoiding_on_obstacle(self, sm):
        sm._change_state(State.CHASING)
        sm.update(cat_detected=True, obstacle_detected=True,
                  gamepad_active=False)
        assert sm.state == State.AVOIDING

    def test_chasing_to_seeking_on_cat_lost(self, sm):
        sm._change_state(State.CHASING)
        sm._last_cat_seen_time = time.time() - 10  # Long ago

        with patch("src.control.state_machine.CAT_LOST_TIMEOUT", 0.0):
            sm.update(cat_detected=False, obstacle_detected=False,
                      gamepad_active=False)
        assert sm.state == State.SEEKING

    def test_gamepad_overrides_to_manual(self, sm):
        sm._change_state(State.CHASING)
        sm.update(cat_detected=True, obstacle_detected=False,
                  gamepad_active=True)
        assert sm.state == State.MANUAL

    def test_manual_exits_to_idle(self, sm):
        sm._change_state(State.MANUAL)
        sm.exit_manual()
        assert sm.state == State.IDLE

    def test_avoiding_returns_to_seeking(self, sm):
        sm._change_state(State.AVOIDING)
        sm._state_start_time = time.time() - 10  # Long ago
        sm.update(cat_detected=False, obstacle_detected=False,
                  gamepad_active=False)
        assert sm.state == State.SEEKING

    def test_obstacle_does_not_override_manual(self, sm):
        sm._change_state(State.MANUAL)
        sm._manual_requested = True
        sm.update(cat_detected=False, obstacle_detected=True,
                  gamepad_active=True)
        assert sm.state == State.MANUAL

    def test_seeking_direction_alternates(self, sm):
        sm._change_state(State.SEEKING)
        initial = sm.seeking_direction

        with patch("src.control.state_machine.SEEKING_SPIN_DURATION", 0.0):
            sm.update(cat_detected=False, obstacle_detected=False,
                      gamepad_active=False)

        assert sm.seeking_direction == -initial

    def test_time_in_state(self, sm):
        assert sm.time_in_state >= 0
        assert sm.time_in_state < 1.0  # Just created


class TestStateTransitionSafety:
    """Verify no invalid state transitions can occur."""

    def test_cannot_go_directly_from_idle_to_chasing(self, sm):
        """IDLE should go to SEEKING first, not directly to CHASING."""
        sm.update(cat_detected=True, obstacle_detected=False,
                  gamepad_active=False)
        # Still in IDLE because IDLE_DURATION hasn't elapsed
        assert sm.state == State.IDLE

    def test_obstacle_avoidance_takes_priority(self, sm):
        """Obstacle avoidance should override seeking."""
        sm._change_state(State.SEEKING)
        sm.update(cat_detected=False, obstacle_detected=True,
                  gamepad_active=False)
        assert sm.state == State.AVOIDING
