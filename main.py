import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

# Храним состояние (ждём ли доход или расход от пользователя)
user_state = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 👋 Я бот для учёта финансов.\n"
        "Нажми /add, чтобы внести расход или доход."
    )

# /add → показываем кнопки "Расход" и "Доход"
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

# Обработка кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "income":
        user_state[query.from_user.id] = "income"
        await query.message.reply_text("Введи сумму дохода (₽):")
    elif query.data == "expense":
        user_state[query.from_user.id] = "expense"
        await query.message.reply_text("Введи сумму расхода (₽):")

# Обработка ввода суммы (когда пишем число после выбора кнопки)
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

    # Сохраняем в файл
    with open("finance.txt", "a") as f:
        f.write(f"{amount}\n")

    # Сбросим состояние
    user_state[user_id] = None

    await update.message.reply_text(f"✅ Записал: {amount} ₽")

# /stats → показать баланс
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("finance.txt", "r") as f:
            amounts = [float(x.strip()) for x in f.readlines()]
    except FileNotFoundError:
        amounts = []

    total = sum(amounts)
    await update.message.reply_text(f"💰 Баланс: {total} ₽")

def main():
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

if __name__ == "__main__":
    main()
