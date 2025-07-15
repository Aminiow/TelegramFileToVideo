import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from main import format_eta, progress_bar, abort_flags, build_abort_keyboard

@pytest.mark.asyncio
async def test_build_abort_keyboard():
    keyboard = build_abort_keyboard()
    assert keyboard.inline_keyboard[0][0].text == "❌ Abort"
    assert keyboard.inline_keyboard[0][0].callback_data == "abort"

def test_progress_bar_values():
    bar = progress_bar(0.0)
    assert bar == "░" * 20
    bar = progress_bar(1.0)
    assert bar == "█" * 20
    bar = progress_bar(0.5)
    assert bar.count("█") == 10
    assert bar.count("░") == 10

def test_format_eta_output():
    start = 1000.0
    current = 50
    total = 100
    eta = format_eta(start, current, total)
    assert isinstance(eta, str)
    # output should contain 'left'
    assert "left" in eta

@pytest.mark.asyncio
async def test_abort_flag_behavior():
    abort_flags.clear()
    message_id = 9999
    abort_flags[message_id] = False
    assert abort_flags[message_id] is False
    abort_flags[message_id] = True
    assert abort_flags[message_id] is True

@pytest.mark.asyncio
async def test_edit_progress_calls(monkeypatch):
    # Mock message.edit to track calls
    class DummyMessage:
        def __init__(self):
            self.edited_text = None
        async def edit(self, text, reply_markup=None):
            self.edited_text = text
            return True

    dummy_msg = DummyMessage()
    current = 50
    total = 100
    start_time = 1000.0

    # Patch the edit method to our dummy
    await main.edit_progress(dummy_msg, "Test progress", current, total, start_time)
    assert dummy_msg.edited_text is not None
    assert "Test progress" in dummy_msg.edited_text
