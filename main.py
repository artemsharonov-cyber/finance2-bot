import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# /start команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🎉 Я бот для учёта расходов и доходов.\n"
        "➕ Добавить расход или доход: /add 500\n"
        "📊 Посмотреть баланс: /stats"
    )

# /add <сумма>
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Укажи число. Пример: /add 500")
        return
    
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Нужно именно число. Пример: /add 1200")
        return
    
    with open("finance.txt", "a") as f:
        f.write(f"{amount}\n")
    
    await update.message.reply_text(f"✅ Записал: {amount}")

# /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("finance.txt", "r") as f:
            amounts = [float(x.strip()) for x in f.readlines()]
    except FileNotFoundError:
        amounts = []

    total = sum(amounts)
    await update.message.reply_text(f"💰 Баланс: {total}")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ Ошибка: переменная BOT_TOKEN не установлена")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("stats", stats))
    app.run_polling()

if __name__ == "__main__":
    main()
