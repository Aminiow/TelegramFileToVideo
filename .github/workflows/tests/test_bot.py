import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from .main import (  # Replace with your actual filename without .py
    app,
    progress_bar,
    format_eta,
    abort_flags,
    build_abort_keyboard,
    edit_progress,
    abort_callback,
    handle_video_as_file,
    start_command,
)

class DummyMessage:
    def __init__(self):
        self.text = ""
        self.id = 123
        self.chat = MagicMock()
        self.from_user = MagicMock()
        self.reply_text = AsyncMock(return_value=self)
        self.edit_text = AsyncMock(return_value=self)
        self.edit = AsyncMock(return_value=self)
        self.caption = None
        self.document = None

class DummyCallbackQuery:
    def __init__(self, message):
        self.message = message
        self.data = "abort"
        self.from_user = MagicMock()
        self.answer = AsyncMock()

@pytest.mark.asyncio
async def test_progress_bar_and_eta():
    bar = progress_bar(0.5)
    assert len(bar) == 20
    assert bar.count("█") == 10
    eta_str = format_eta(time.time()-10, 5, 10)
    assert "left" in eta_str

@pytest.mark.asyncio
async def test_abort_callback():
    message = DummyMessage()
    cbq = DummyCallbackQuery(message)
    await abort_callback(app, cbq)
    assert abort_flags.get(message.id) == True
    cbq.answer.assert_called_once()
    message.edit_text.assert_called_once_with("❌ Operation aborted by user.")

@pytest.mark.asyncio
async def test_start_command():
    msg = DummyMessage()
    await start_command(app, msg)
    msg.reply_text.assert_called_once()
    args = msg.reply_text.call_args[0][0]
    assert "Send or forward me a video" in args

@pytest.mark.asyncio
async def test_handle_video_as_file_nonvideo():
    msg = DummyMessage()
    msg.document = MagicMock()
    msg.document.mime_type = "application/pdf"
    await handle_video_as_file(app, msg)
    msg.reply_text.assert_called_with("⚠️ This document is not a video.")

@pytest.mark.asyncio
async def test_handle_video_as_file_video(monkeypatch):
    msg = DummyMessage()
    msg.document = MagicMock()
    msg.document.mime_type = "video/mp4"
    msg.document.file_name = "test.mp4"
    msg.chat.id = 1111
    msg.from_user.id = 2222

    # Patch download_media to simulate download
    async def fake_download_media(message, progress=None):
        if progress:
            await progress(50, 100)
            await progress(100, 100)
        return "/tmp/fakefile.mp4"

    # Patch send_video to simulate upload
    async def fake_send_video(**kwargs):
        if kwargs.get("progress"):
            await kwargs["progress"](50, 100)
            await kwargs["progress"](100, 100)
        return True

    monkeypatch.setattr(app, "download_media", fake_download_media)
    monkeypatch.setattr(app, "send_video", fake_send_video)

    await handle_video_as_file(app, msg)

    # Should have called reply_text multiple times for progress updates
    assert msg.reply_text.call_count >= 2

@pytest.mark.asyncio
async def test_edit_progress_handles_exceptions():
    msg = DummyMessage()
    # Force edit to raise Exception once
    async def raise_exc(text, reply_markup=None):
        raise Exception("edit failed")
    msg.edit = raise_exc
    # Should not raise
    await edit_progress(msg, "Testing", 5, 10, time.time())

@pytest.mark.asyncio
async def test_build_abort_keyboard():
    kb = build_abort_keyboard()
    assert hasattr(kb, "inline_keyboard")
    assert kb.inline_keyboard[0][0].text == "❌ Abort"
