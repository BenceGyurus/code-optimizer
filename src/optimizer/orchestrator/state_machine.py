from enum import Enum, auto
from typing import Set, Dict

class State(Enum):
    INIT = auto()
    BASELINE_READY = auto()
    PROFILE_READY = auto()
    ANALYSIS_READY = auto()
    PATCH_PROPOSED = auto()
    PATCH_APPLIED = auto()
    VERIFIED = auto()
    REMEASURED = auto()
    DONE = auto()
    FAILED = auto()

class StateMachine:
    def __init__(self, initial_state: State = State.INIT):
        self._current_state = initial_state
        self._transitions: Dict[State, Set[State]] = {
            State.INIT: {State.BASELINE_READY, State.FAILED},
            State.BASELINE_READY: {State.PROFILE_READY, State.ANALYSIS_READY, State.FAILED},
            State.PROFILE_READY: {State.ANALYSIS_READY, State.FAILED},
            State.ANALYSIS_READY: {State.PATCH_PROPOSED, State.FAILED},
            State.PATCH_PROPOSED: {State.PATCH_APPLIED, State.ANALYSIS_READY, State.FAILED},
            State.PATCH_APPLIED: {State.VERIFIED, State.FAILED},
            State.VERIFIED: {State.REMEASURED, State.ANALYSIS_READY, State.FAILED},
            State.REMEASURED: {State.ANALYSIS_READY, State.DONE, State.FAILED},
            State.DONE: set(),
            State.FAILED: set(),
        }

    @property
    def current_state(self) -> State:
        return self._current_state

    def transition_to(self, next_state: State) -> bool:
        """Attempt to transition to a new state. Returns True if successful."""
        if next_state == State.FAILED:
            self._current_state = next_state
            return True
            
        allowed = self._transitions.get(self._current_state, set())
        if next_state in allowed:
            self._current_state = next_state
            return True
        return False

    def is_allowed(self, next_state: State) -> bool:
        """Check if a transition to next_state is allowed from current_state."""
        if next_state == State.FAILED:
            return True
        return next_state in self._transitions.get(self._current_state, set())

    def force_terminal(self, terminal_state: State) -> None:
        """Force a controlled terminal state for guardrail stops."""
        if terminal_state not in {State.DONE, State.FAILED}:
            raise ValueError("Only DONE or FAILED can be forced as terminal states.")
        self._current_state = terminal_state

    def __repr__(self):
        return f"StateMachine(state={self._current_state.name})"
