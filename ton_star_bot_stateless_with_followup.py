from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import requests
import json
import os

# Telegram ID разработчика
DEVELOPER_ID = 863589590

# Курсы
STORE_USD_PER_STAR = 0.0239
FRAGMENT_USD_PER_STAR = 0.015

user_state = {}
waiting_for_issue = set()
USERS_FILE = "users.json"

# Загрузка ID пользователей
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

# Сохранение ID пользователей
def save_users(user_ids):
    with open(USERS_FILE, "w") as f:
        json.dump(list(user_ids), f)

known_users = load_users()

# Получение цены TON
def get_ton_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "the-open-network", "vs_currencies": "usd"}
        response = requests.get(url, params=params)
        data = response.json()
        return float(data["the-open-network"]["usd"])
    except:
        return None

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in known_users:
        known_users.add(user_id)
        save_users(known_users)

    keyboard = [
        [InlineKeyboardButton("Fragment Store", callback_data="fragment")],
        [InlineKeyboardButton("Telegram Store", callback_data="store")]
    ]
    await update.message.reply_text(
        "Привет! Я бот-калькулятор Stars в TON.\n\nВыбери платформу:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Команда /select_store
async def handle_select_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Fragment Store", callback_data="fragment")],
        [InlineKeyboardButton("Telegram Store", callback_data="store")]
    ]
    await update.message.reply_text("Выбери магазин:", reply_markup=InlineKeyboardMarkup(keyboard))

# Команда /change_direction
async def handle_change_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_state or "store" not in user_state[user_id]:
        await update.message.reply_text("Сначала выбери магазин через /select_store.")
        return

    keyboard = [
        [InlineKeyboardButton("Звёзды → TON", callback_data="stars_to_ton")],
        [InlineKeyboardButton("TON → Звёзды", callback_data="ton_to_stars")]
    ]
    await update.message.reply_text("Выбери направление перевода:", reply_markup=InlineKeyboardMarkup(keyboard))

# Команда /issue — обращение к разработчику
async def issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    waiting_for_issue.add(user_id)
    await update.message.reply_text("Напиши сообщение для разработчика — пожелание или описание проблемы.")

# Команда /users — статистика (только для разработчика)
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != DEVELOPER_ID:
        await update.message.reply_text("Эта команда доступна только разработчику.")
        return
    await update.message.reply_text(f"Всего пользователей: {len(known_users)}")

# Обработка кнопок (магазин)
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
    await query.edit_message_text("Теперь выбери направление конвертации:", reply_markup=InlineKeyboardMarkup(keyboard))

# Обработка кнопок (направление)
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

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in waiting_for_issue:
        user = update.message.from_user
        text = update.message.text
        await context.bot.send_message(
            chat_id=DEVELOPER_ID,
            text=f"Обращение от @{user.username or 'без имени'} (ID: {user.id}):\n{text}"
        )
        await update.message.reply_text("Сообщение отправлено разработчику!")
        waiting_for_issue.remove(user_id)
        return

    if user_id not in user_state or "store" not in user_state[user_id] or "direction" not in user_state[user_id]:
        await update.message.reply_text("Сначала выбери магазин и направление через /start.")
        return

    try:
        amount = float(update.message.text.replace(',', '.'))
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число.")
        return

    ton_price = get_ton_price()
    if ton_price is None:
        await update.message.reply_text("Не удалось получить курс TON.")
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

# Запуск
def main():
    application = Application.builder().token("7612436248:AAGC7q5wLLs7_plfhoKL9JMPD4zvkZq1Tx8").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("select_store", handle_select_store))
    application.add_handler(CommandHandler("change_direction", handle_change_direction))
    application.add_handler(CommandHandler("issue", issue))
    application.add_handler(CommandHandler("users", users))

    application.add_handler(CallbackQueryHandler(handle_store_choice, pattern="^(fragment|store)$"))
    application.add_handler(CallbackQueryHandler(handle_direction_choice, pattern="^(stars_to_ton|ton_to_stars)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
