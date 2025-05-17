from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import requests

STORE_USD_PER_STAR = 0.0239
FRAGMENT_USD_PER_STAR = 0.015

user_state = {}

def get_ton_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "the-open-network", "vs_currencies": "usd"}
        response = requests.get(url, params=params)
        data = response.json()
        return float(data["the-open-network"]["usd"])
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Fragment Store", callback_data="fragment")],
        [InlineKeyboardButton("Telegram Store", callback_data="store")]
    ]
    await update.message.reply_text(
        "Привет! Я бот-калькулятор Stars в TON.\n\nВыбери платформу:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_store_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def change_direction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_state or "store" not in user_state[user_id]:
        await update.message.reply_text("Сначала выбери магазин с помощью /select_store")
        return

    keyboard = [
        [InlineKeyboardButton("Звёзды → TON", callback_data="stars_to_ton")],
        [InlineKeyboardButton("TON → Звёзды", callback_data="ton_to_stars")]
    ]
    await update.message.reply_text(
        "Выбери направление перевода:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_store_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    store = query.data
    user_id = query.from_user.id
    user_state[user_id] = {"store": store}

    keyboard = [
        [InlineKeyboardButton("Звёзды → TON", callback_data="stars_to_ton")],
        [InlineKeyboardButton("TON → Звёзды", callback_data="ton_to_stars")]
    ]
    await query.edit_message_text(
        "Теперь выбери направление конвертации:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_direction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    direction = query.data
    user_id = query.from_user.id

    if user_id in user_state:
        user_state[user_id]["direction"] = direction
        await query.edit_message_text("Введи количество:")
    else:
        await query.edit_message_text("Сначала выбери магазин через /start")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_state or "store" not in user_state[user_id] or "direction" not in user_state[user_id]:
        await update.message.reply_text("Пожалуйста, начни с команды /start и выбери магазин и направление.")
        return

    try:
        amount = float(update.message.text.replace(',', '.'))
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число.")
        return

    ton_price = get_ton_price()
    if ton_price is None:
        await update.message.reply_text("Не удалось получить курс TON. Попробуйте позже.")
        return

    data = user_state[user_id]
    store = data["store"]
    direction = data["direction"]
    usd_per_star = FRAGMENT_USD_PER_STAR if store == "fragment" else STORE_USD_PER_STAR

    if direction == "stars_to_ton":
        total_usd = amount * usd_per_star
        total_ton = total_usd / ton_price
        result = f"{amount} звёзд по {store} ≈ {total_usd:.2f} $ ≈ {total_ton:.4f} TON"
    else:
        total_usd = amount * ton_price
        total_stars = total_usd / usd_per_star
        result = f"{amount} TON по {store} ≈ {total_usd:.2f} $ ≈ {total_stars:.0f} звёзд"

    await update.message.reply_text(result)

def main():
    app = ApplicationBuilder().token("7612436248:AAGSzcdng_0HsCwk9WzjqG_rOveZzV-0dGI").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("select_store", select_store_command))
    app.add_handler(CommandHandler("change_direction", change_direction_command))
    app.add_handler(CallbackQueryHandler(handle_store_choice, pattern="^(fragment|store)$"))
    app.add_handler(CallbackQueryHandler(handle_direction_choice, pattern="^(stars_to_ton|ton_to_stars)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()