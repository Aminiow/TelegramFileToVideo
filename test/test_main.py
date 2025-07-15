import pytest
import time
from main import format_eta, progress_bar, abort_flags

def test_format_eta_typical():
    start = time.time() - 10  # started 10 seconds ago
    eta = format_eta(start, 50, 100)
    assert isinstance(eta, str)
    assert "left" in eta

def test_format_eta_zero_speed():
    # current = 0 means speed zero, eta should be 0s left or similar
    start = time.time()
    eta = format_eta(start, 0, 100)
    assert isinstance(eta, str)

def test_progress_bar_length():
    bar = progress_bar(0.5)
    assert len(bar) == 20
    assert bar.count("█") == 10
    assert bar.count("░") == 10

def test_abort_flags():
    # Initially no abort
    abort_flags.clear()
    message_id = 12345
    abort_flags[message_id] = False
    assert abort_flags[message_id] is False

    # Set abort true
    abort_flags[message_id] = True
    assert abort_flags[message_id] is True
