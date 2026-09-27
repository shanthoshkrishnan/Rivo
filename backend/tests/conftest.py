import pytest
from app.core.circuit_breaker import circuit_breaker
from app.core.request_tracker import reset_current_tracker


@pytest.fixture(autouse=True)
def reset_circuit_and_tracker():
    """Ensure circuit breaker and budget tracker state do not leak across tests."""
    circuit_breaker.reset()
    reset_current_tracker()
    yield
    circuit_breaker.reset()
    reset_current_tracker()
