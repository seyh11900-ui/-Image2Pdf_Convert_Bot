import io
import os
import logging
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Fetch token safely from Railway environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["images"] = []
    welcome_text = (
        "👋 **Welcome to Image to PDF Bot!**\n\n"
        "Send me photos, and I will combine them into a single PDF file.\n\n"
        "**Available Commands:**\n"
        "• /start - Reset bot & show welcome\n"
        "• /help - Instructions & details\n"
        "• /status - Check uploaded photo count\n"
        "• /clear - Delete all queued photos"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ **How to use this bot:**\n\n"
        "1️⃣ Send photos directly to this chat.\n"
        "2️⃣ Click **📄 Convert to PDF** when ready.\n"
        "3️⃣ Download your completed PDF!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    images = context.user_data.get("images", [])
    count = len(images)
    if count == 0:
        await update.message.reply_text("📥 Your queue is empty. Send photos to begin!")
    else:
        keyboard = [
            [InlineKeyboardButton(f"📄 Convert to PDF ({count})", callback_data="convert")],
            [InlineKeyboardButton("🗑️ Clear Images", callback_data="clear")]
        ]
        await update.message.reply_text(
            f"📊 You have **{count}** image{'s' if count > 1 else ''} queued.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["images"] = []
    await update.message.reply_text("🗑️ Cleared all queued images.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "images" not in context.user_data:
        context.user_data["images"] = []

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    img = Image.open(io.BytesIO(photo_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")

    context.user_data["images"].append(img)
    count = len(context.user_data["images"])

    keyboard = [
        [InlineKeyboardButton(f"📄 Convert to PDF ({count})", callback_data="convert")],
        [InlineKeyboardButton("🗑️ Clear Images", callback_data="clear")]
    ]
    await update.message.reply_text(
        f"✅ Photo #{count} received!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "convert":
        images = context.user_data.get("images", [])
        if not images:
            await query.edit_message_text("⚠️ No images found! Send photos first.")
            return

        await query.edit_message_text("⏳ Generating PDF document...")

        pdf_bytes = io.BytesIO()
        first_img = images[0]
        other_imgs = images[1:] if len(images) > 1 else []

        first_img.save(pdf_bytes, format="PDF", save_all=True, append_images=other_imgs)
        pdf_bytes.seek(0)

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_bytes,
            filename="converted_images.pdf",
            caption=f"🎉 Converted {len(images)} images into PDF!"
        )
        context.user_data["images"] = []

    elif query.data == "clear":
        context.user_data["images"] = []
        await query.edit_message_text("🗑️ Cleared all queued images.")


def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is missing!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()


if __name__ == "__main__":
    main()
