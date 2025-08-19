import os
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters,
)

user_state = {}

# --- Telegram Handlers ---
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
    q = update.callback_query
    await q.answer()
    if q.data == "income":
        user_state[q.from_user.id] = "income"
        await q.message.reply_text("Введи сумму дохода (₽):")
    else:
        user_state[q.from_user.id] = "expense"
        await q.message.reply_text("Введи сумму расхода (₽):")

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    state = user_state.get(uid)
    if not state:
        return
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Нужно число")
        return

    if state == "expense":
        amount = -abs(amount)

    with open("finance.txt", "a") as f:
        f.write(f"{amount}\n")

    user_state[uid] = None
    await update.message.reply_text(f"✅ Добавлено {amount} ₽")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("finance.txt") as f:
            nums = [float(x) for x in f]
    except FileNotFoundError:
        nums = []
    await update.message.reply_text(f"💰 Баланс: {sum(nums)} ₽")

# --- Render healthcheck ---
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
    print(f"🌍 Web server on port {port}")

# --- Main ---
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

    # запускаем healthcheck параллельно
    asyncio.create_task(run_web())

    # ручной запуск Telegram-бота
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    await bot.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
