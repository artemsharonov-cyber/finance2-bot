import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

# Храним, что выбрал пользователь (доход или расход)
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

# обработка числа
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_state.get(user_id)

    if not state:
        await update.message.reply_text("Сначала используй /add и выбери расход или доход.")
        return

    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Нужно ввести число. Пример: 1200")
        return

    if state == "expense":
        amount = -abs(amount)  # расход = минус
    else:
        amount = abs(amount)   # доход = плюс

    # сохраняем в файл
    with open("finance.txt", "a") as f:
        f.write(f"{amount}\n")

    user_state[user_id] = None  # сброс состояния

    await update.message.reply_text(f"✅ Записано: {amount} ₽")

# /stats → показывает баланс
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("finance.txt", "r") as f:
            nums = [float(x.strip()) for x in f.readlines()]
    except FileNotFoundError:
        nums = []

    total = sum(nums)
    await update.message.reply_text(f"💰 Баланс: {total} ₽")

# запускаем бота
def run_bot():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ Ошибка: переменная BOT_TOKEN не найдена")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))

    app.run_polling()

# запускаем фейковый веб‑сервер для Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_web():
    port = int(os.environ.get("PORT", 10000))  # Render сам задаёт PORT
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

if __name__ == "__main__":
    # бот запускается в отдельном потоке
    threading.Thread(target=run_bot, daemon=True).start()
    # основной поток держит веб‑сервер (для Render)
    run_web()
