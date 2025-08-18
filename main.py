import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

user_state = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 👋 Я бот для учёта финансов.\n"
        "Нажми /add, чтобы внести расход или доход.\n"
        "Посмотреть баланс: /stats"
    )

# /add → показываем кнопки
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("💸 Расход", callback_data="expense"),
            InlineKeyboardButton("💵 Доход", callback_data="income"),
        ]
    ]
    await update.message.reply_text(
        "Что добавить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# обработка выбора кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "income":
        user_state[query.from_user.id] = "income"
        await query.message.reply_text("Введи сумму дохода (₽):")
    elif query.data == "expense":
        user_state[query.from_user.id] = "expense"
        await query.message.reply_text("Введи сумму расхода (₽):")

# обработка суммы
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_state.get(user_id)
    if not state:
        await update.message.reply_text("Сначала используй /add и выбери расход или доход.")
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

# /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("finance.txt", "r") as f:
            nums = [float(x.strip()) for x in f.readlines()]
    except FileNotFoundError:
        nums = []
    total = sum(nums)
    await update.message.reply_text(f"💰 Баланс: {total} ₽")

# HTTP-заглушка для Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

def run_bot():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN не задан")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))

    app.run_polling()  # правильно, без asyncio.run

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    threading.Thread(target=run_bot, daemon=True).start()
    # Render видит порт — держим процесс живым
    run_web()
