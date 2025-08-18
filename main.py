import os
import threading
from aiohttp import web
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters,
)

user_state = {}

# --- Telegram bot handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 👋 Я бот для учёта финансов.\n"
        "Нажми /add, чтобы внести расход или доход.\n"
        "Посмотреть баланс: /stats"
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("💸 Расход", callback_data="expense"),
        InlineKeyboardButton("💵 Доход", callback_data="income"),
    ]]
    await update.message.reply_text("Что добавить?", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "income":
        user_state[query.from_user.id] = "income"
        await query.message.reply_text("Введи сумму дохода (₽):")
    elif query.data == "expense":
        user_state[query.from_user.id] = "expense"
        await query.message.reply_text("Введи сумму расхода (₽):")

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_state.get(user_id)
    if not state:
        await update.message.reply_text("Сначала /add и выбери расход или доход.")
        return
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Нужно число. Пример: 1200")
        return
    if state == "expense":
        amount = -abs(amount)
    else:
        amount = abs(amount)

    with open("finance.txt", "a") as f:
        f.write(f"{amount}\n")

    user_state[user_id] = None
    await update.message.reply_text(f"✅ Записано: {amount} ₽")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("finance.txt", "r") as f:
            nums = [float(x.strip()) for x in f.readlines()]
    except FileNotFoundError:
        nums = []
    await update.message.reply_text(f"💰 Баланс: {sum(nums)} ₽")

# --- HTTP healthcheck for Render ---
async def handle_health(request):
    return web.Response(text="Bot is running")

def run_web():
    app = web.Application()
    app.router.add_get("/", handle_health)
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

# --- Main ---
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN не задан")

    print("🚀 Запускаем бота...")

    tg_app = Application.builder().token(token).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("add", add))
    tg_app.add_handler(CommandHandler("stats", stats))
    tg_app.add_handler(CallbackQueryHandler(button))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))

    # запустим http-сервер в отдельном фоне
    threading.Thread(target=run_web, daemon=True).start()

    # запустим Telegram-бота
    tg_app.run_polling()

if __name__ == "__main__":
    main()
