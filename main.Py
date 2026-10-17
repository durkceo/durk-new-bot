import os

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

MENU = ReplyKeyboardMarkup(
    [["Home", "Help", "About"]],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome! Choose an option below.",
        reply_markup=MENU,
    )


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        "Choose Home, Help, or About from the menu.",
        reply_markup=MENU,
    )


async def about_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        "I'm a simple Telegram bot written in Python.",
        reply_markup=MENU,
    )


async def handle_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    choice = update.message.text.strip().lower()

    if choice == "home":
        reply = "You're at the home menu."
    elif choice == "help":
        reply = "Choose a button below to see what the bot can do."
    elif choice == "about":
        reply = "I'm a simple Telegram bot written in Python."
    else:
        reply = "Please choose Home, Help, or About from the menu."

    await update.message.reply_text(reply, reply_markup=MENU)


def main() -> None:
    if not TOKEN:
        raise SystemExit("Set the TELEGRAM_BOT_TOKEN environment variable first.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()