import os
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters,
)

user_state = {}

# --- Хендлеры Telegram ---
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
    await update.message.reply_text(f"✅ Добавлено: {amount} ₽")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("finance.txt") as f:
            nums = [float(x.strip()) for x in f.readlines()]
    except FileNotFoundError:
        nums = []
    await update.message.reply_text(f"💰 Баланс: {sum(nums)} ₽")

# --- Healthcheck для Render ---
async def handle_health(request):
    return web.Response(text="Bot is running")

async def run_web():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌍 Web server listening on port {port}")

# --- Главный запуск ---
async def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN не найден")

    print("🚀 Запускаем бота...")

    bot = Application.builder().token(token).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("add", add))
    bot.add_handler(CommandHandler("stats", stats))
    bot.add_handler(CallbackQueryHandler(button))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))

    # Запускаем и веб-сервер, и бота
    await run_web()             # Render healthcheck
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    await bot.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
