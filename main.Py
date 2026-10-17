import os
import sqlite3
from datetime import datetime, timezone

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or 0)
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@")
DB_FILE = "bot_data.sqlite3"

# Edit these packages whenever you want to change your shop.
PACKAGES = [
    {
        "name": "Basic",
        "price": "5",
        "description": "Basic package with standard features.",
    },
    {
        "name": "Standard",
        "price": "10",
        "description": "Standard package with extra features.",
    },
    {
        "name": "Premium",
        "price": "20",
        "description": "Premium package with all listed features.",
    },
]


def connect_db():
    return sqlite3.connect(DB_FILE)


def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                referred_by INTEGER,
                joined_at TEXT NOT NULL
            )
        """)


def register_user(user, referral_id=None):
    with connect_db() as db:
        existing = db.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user.id,),
        ).fetchone()

        if existing:
            db.execute(
                "UPDATE users SET username = ?, first_name = ? "
                "WHERE user_id = ?",
                (user.username, user.first_name, user.id),
            )
            return False

        # Only accept referrals from an existing, different user.
        if referral_id == user.id:
            referral_id = None

        if referral_id is not None:
            referrer = db.execute(
                "SELECT user_id FROM users WHERE user_id = ?",
                (referral_id,),
            ).fetchone()
            if not referrer:
                referral_id = None

        db.execute(
            """
            INSERT INTO users
                (user_id, username, first_name, referred_by, joined_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.username,
                user.first_name,
                referral_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return True


def get_referral_count(user_id):
    with connect_db() as db:
        return db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by = ?",
            (user_id,),
        ).fetchone()[0]


def get_stats():
    with connect_db() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]
        referrals = db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL"
        ).fetchone()[0]
    return total, referrals


def make_menu(user_id):
    rows = [
        ["Home", "Services"],
        ["Prices", "Contact"],
        ["Refer a Friend", "My Referrals"],
        ["Help", "About"],
    ]

    if ADMIN_USER_ID and user_id == ADMIN_USER_ID:
        rows.append(["Admin"])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referral_id = None

    if context.args:
        payload = context.args[0]
        if payload.startswith("ref_"):
            try:
                referral_id = int(payload[4:])
            except ValueError:
                referral_id = None

    is_new_user = register_user(user, referral_id)
    menu = make_menu(user.id)

    message = "Welcome! Choose an option below."

    if is_new_user and referral_id and referral_id != user.id:
        message += "\nYour referral link has been recorded if it was valid."

    await update.effective_message.reply_text(
        message,
        reply_markup=menu,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Use the menu buttons to view services, prices, contact details, "
        "and your referral link.",
        reply_markup=make_menu(update.effective_user.id),
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "I'm a Telegram shop and referral bot written in Python.",
        reply_markup=make_menu(update.effective_user.id),
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"Your Telegram user ID is: {update.effective_user.id}"
    )


async def show_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["Available packages:\n"]
    for package in PACKAGES:
        lines.append(
            f"**{package['name']}** — £{package['price']}\n"
            f"{package['description']}\n"
        )

    await update.effective_message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=make_menu(update.effective_user.id),
    )


async def referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start=ref_{user.id}"
    count = get_referral_count(user.id)

    await update.effective_message.reply_text(
        f"Your personal referral link:\n{link}\n\n"
        f"Recorded referrals: {count}\n\n"
        "A referral is counted when a new user starts the bot through "
        "your link. Existing users are not counted again.",
        reply_markup=make_menu(user.id),
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not ADMIN_USER_ID or user.id != ADMIN_USER_ID:
        await update.effective_message.reply_text("Access denied.")
        return

    total, referrals = get_stats()
    await update.effective_message.reply_text(
        "Admin panel\n\n"
        f"Registered users: {total}\n"
        f"Successful referral registrations: {referrals}\n\n"
        "Use /stats to view these figures again.",
        reply_markup=make_menu(user.id),
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_USER_ID or update.effective_user.id != ADMIN_USER_ID:
        await update.effective_message.reply_text("Access denied.")
        return

    total, referrals = get_stats()
    await update.effective_message.reply_text(
        f"Registered users: {total}\n"
        f"Successful referral registrations: {referrals}"
    )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    choice = update.effective_message.text.strip().lower()
    menu = make_menu(user.id)

    if choice == "home":
        reply = "You're at the home menu."

    elif choice == "services":
        reply = (
            "Our services:\n"
            "• Basic package\n"
            "• Standard package\n"
            "• Premium package\n\n"
            "Tap Prices to see package details."
        )

    elif choice == "prices":
        await show_packages(update, context)
        return

    elif choice == "contact":
        if SUPPORT_USERNAME:
            reply = f"Contact support: https://t.me/{SUPPORT_USERNAME}"
        else:
            reply = "Support contact has not been configured yet."

    elif choice == "refer a friend":
        await referral_info(update, context)
        return

    elif choice == "my referrals":
        await referral_info(update, context)
        return

    elif choice == "help":
        reply = "Choose a menu button to explore the bot."

    elif choice == "about":
        reply = "I'm a Telegram shop and referral bot written in Python."

    elif choice == "admin":
        await admin_panel(update, context)
        return

    else:
        reply = "Please choose an option using the menu buttons."

    await update.effective_message.reply_text(reply, reply_markup=menu)


def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing from the environment.")

    init_db()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()