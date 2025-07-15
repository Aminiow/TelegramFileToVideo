import os
import time
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Configure logging (console + file)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("video_converter_bot.log"),
        logging.StreamHandler()
    ]
)

API_ID = 2607941
API_HASH = "c1c7f3e393497fed7754acc1362fccdf"
BOT_TOKEN = "6397548584:AAGm44F0A78_LZRVKljWYDcMyZYeyaqRKPE"

app = Client(
    "video_converter_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Store abort states: message_id -> bool
abort_flags = {}

def format_eta(start, current, total):
    elapsed = time.time() - start
    speed = current / elapsed if elapsed > 0 else 0
    remaining = (total - current) / speed if speed > 0 else 0
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    if minutes > 0:
        return f"{minutes}m {seconds}s left"
    else:
        return f"{seconds}s left"

def progress_bar(progress):
    # progress: 0.0 - 1.0
    blocks = int(progress * 20)
    return "█" * blocks + "░" * (20 - blocks)

def build_abort_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Abort", callback_data="abort")]]
    )

async def edit_progress(message: Message, prefix: str, current: int, total: int, start_time: float):
    percent = current / total
    bar = progress_bar(percent)
    eta = format_eta(start_time, current, total)
    text = f"{prefix}\n{bar} {int(percent * 100)}%\n⏳ ETA: {eta}"
    try:
        await message.edit(text, reply_markup=build_abort_keyboard())
    except Exception as e:
        logging.warning(f"Edit error ({prefix.lower()}): {e}")

@app.on_callback_query(filters.regex(r"^abort$"))
async def abort_callback(client: Client, callback_query: CallbackQuery):
    message = callback_query.message
    abort_flags[message.id] = True
    await callback_query.answer("Abort requested. Stopping...", show_alert=True)
    await message.edit_text("❌ Operation aborted by user.")

@app.on_message(filters.document & (filters.forwarded | filters.outgoing | filters.private))
async def handle_video_as_file(client: Client, message: Message):
    doc = message.document
    if not doc or not doc.mime_type or not doc.mime_type.startswith("video"):
        await message.reply_text("⚠️ This document is not a video.")
        return

    chat_id = message.chat.id

    # Prepare abort button
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Abort", callback_data="abort")]]
    )

    logging.info(f"Started processing file {doc.file_name} from user {message.from_user.id}")

    # Send initial progress message
    progress_message = await message.reply_text("📥 Downloading...\n░░░░░░░░░░░░░░░░░░░░░░░░ 0%\n⏳ ETA: calculating...", reply_markup=keyboard)

    # Download with progress callback
    start_dl = time.time()
    file_path = None

    abort_flags[progress_message.id] = False

    async def progress_callback_dl(current, total):
        if abort_flags.get(progress_message.id, False):
            raise asyncio.CancelledError("Download aborted by user.")
        # Update every 10%
        if total == 0:
            return
        percent = current / total
        step = int(percent * 10)
        if step != progress_callback_dl.last_step:
            progress_callback_dl.last_step = step
            await edit_progress(progress_message, "📥 Downloading...", current, total, start_dl)

    progress_callback_dl.last_step = -1

    try:
        file_path = await client.download_media(message, progress=progress_callback_dl)
    except asyncio.CancelledError:
        logging.info("Download aborted by user.")
        return
    except Exception as e:
        logging.error(f"Download error: {e}")
        await progress_message.edit_text(f"❌ Download failed: {e}")
        return

    # Check abort before upload
    if abort_flags.get(progress_message.id, False):
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    # Upload phase
    await progress_message.edit_text("📤 Uploading...\n░░░░░░░░░░░░░░░░░░░░░░░░ 0%\n⏳ ETA: calculating...", reply_markup=keyboard)
    start_ul = time.time()

    async def progress_callback_ul(current, total):
        if abort_flags.get(progress_message.id, False):
            raise asyncio.CancelledError("Upload aborted by user.")
        percent = current / total
        step = int(percent * 10)
        if step != progress_callback_ul.last_step:
            progress_callback_ul.last_step = step
            await edit_progress(progress_message, "📤 Uploading...", current, total, start_ul)

    progress_callback_ul.last_step = -1

    try:
        await client.send_video(
            chat_id=chat_id,
            video=file_path,
            caption=message.caption or "🎥 Converted video",
            supports_streaming=True,
            progress=progress_callback_ul
        )
    except asyncio.CancelledError:
        logging.info("Upload aborted by user.")
        await progress_message.edit_text("❌ Upload aborted by user.")
        try:
            os.remove(file_path)
        except Exception:
            pass
        return
    except Exception as e:
        logging.error(f"Upload error: {e}")
        await progress_message.edit_text(f"❌ Upload failed: {e}")
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    # Success!
    await progress_message.edit_text("✅ Video sent successfully!")
    logging.info(f"Processed and sent file {doc.file_name} for user {message.from_user.id}")

    # Clean up
    try:
        os.remove(file_path)
    except Exception as e:
        logging.warning(f"Could not delete file {file_path}: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "👋 Hi! Send or forward me a video file as a document, and I'll resend it as a proper streamable video!\n\n"
        "You can abort ongoing operations with the ❌ Abort button."
    )

if __name__ == "__main__":
    logging.info("✅ Bot is running...")
    app.run()