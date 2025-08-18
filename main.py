import os
import threading
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters,
)

user_state = {}

# --- команды ---
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

# --- реакция на нажатие кнопки ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()   # <-- обязательно, иначе Telegram "думает", что кнопка не обработана!

    if query.data == "income":
        user_state[query.from_user.id] = "income"
        await query.message.reply_text("Введи сумму дохода (₽):")
    elif query.data == "expense":
        user_state[query.from_user.id] = "expense"
        await query.message.reply_text("Введи сумму расхода (₽):")

# --- ввод суммы ---
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    state = user_state.get(uid)

    if not state:
        return  # если кнопка не нажата

    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Нужно число, например: 1200")
        return

    if state == "expense":
        amount = -abs(amount)  # расход минус
    else:
        amount = abs(amount)   # доход плюс

    with open("finance.txt", "a") as f:
        f.write(f"{amount}\n")

    user_state[uid] = None
    await update.message.reply_text(f"✅ Добавлено: {amount} ₽")

# --- баланс ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("finance.txt") as f:
            nums = [float(x.strip()) for x in f.readlines()]
    except FileNotFoundError:
        nums = []

    total = sum(nums)
    await update.message.reply_text(f"💰 Баланс: {total} ₽")

# --- HTTP-заглушка для Render ---
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
    tg_app.add_handler(CallbackQueryHandler(button))   # <-- очень важно!
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))

    # aiohttp в главном потоке, бот в фоне
    threading.Thread(target=tg_app.run_polling, daemon=True).start()
    run_web()

if __name__ == "__main__":
    main()
