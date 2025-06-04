import os
import re
import json
import logging
import requests

from config import API_GATEWAY_BASE_URL, BOT_TOKEN
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from tg_repository import (
    init_db,
    get_token,
    save_token
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

(
    ASK_FULLNAME,
    ASK_PHONE,
    ASK_INN,
) = range(3)

PHONE_REGEX = re.compile(r"^(?:\+7|8)\d{10}$")
INN_REGEX = re.compile(r"^\d{10}|\d{12}$")
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    token = get_token(chat_id)
    if token:
        await update.message.reply_text(
            "Авторизация прошла успешно. Здравствуйте! Чем могу помочь?"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Добро пожаловать! Пожалуйста, введите ваши ФИО (полностью)."
        )
        return ASK_FULLNAME


async def ask_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fullname = update.message.text.strip()
    if not fullname or len(fullname.strip().split()) < 3:
        await update.message.reply_text(
            "ФИО не может быть пустым и должно состоять как минимум из 3 слов. Пожалуйста, введите ФИО полностью."
        )
        return ASK_FULLNAME

    context.user_data["fullname"] = fullname
    await update.message.reply_text(
        "Спасибо! Теперь введите номер телефона."
    )
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not PHONE_REGEX.match(phone):
        await update.message.reply_text(
            "Неверный формат телефона. Пожалуйста, введите телефон в формате +7XXXXXXXXXX или 8XXXXXXXXXX."
        )
        return ASK_PHONE

    context.user_data["phone"] = phone
    await update.message.reply_text("Отлично! Теперь введите ваш ИНН.")
    return ASK_INN


async def ask_inn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inn = update.message.text.strip()
    if not INN_REGEX.fullmatch(inn):
        await update.message.reply_text(
            "ИНН должен состоять из 10 или 12 цифр. Попробуйте ещё раз."
        )
        return ASK_INN

    context.user_data["inn"] = inn

    fullname = context.user_data["fullname"]
    phone = context.user_data["phone"]
    user_id_str = str(update.effective_user.id)  # Telegram user ID как пароль

    payload = {
        "fullname": fullname,
        "phone": phone,
        "inn": inn,
        "password": user_id_str,
    }

    try:
        url = f"{API_GATEWAY_BASE_URL.rstrip('/')}/login"
        resp = requests.post(url, json=payload, timeout=10, proxies={"http": None})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Ошибка при запросе /login: {e}")
        await update.message.reply_text(
            "Произошла ошибка при подключении к серверу. Попробуйте позже."
        )
        return ConversationHandler.END

    token = data.get("token")
    if not token:
        await update.message.reply_text(
            "Не удалось получить токен. Проверьте введённые данные или попробуйте позже."
        )
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    save_token(chat_id, token)
    context.user_data["token"] = token

    await update.message.reply_text(
        "Авторизация прошла успешно." 
        "Здравствуйте! Чем могу помочь?"
    )

    return ConversationHandler.END


async def registration_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Регистрация отменена. Если захотите зарегистрироваться — введите /start.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get("token")
    if not token:
        chat_id = update.effective_chat.id
        token = get_token(chat_id)
    if not token:
        await update.message.reply_text(
            "Пожалуйста, сначала авторизуйтесь через /start."
        )
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    headers = {
        "Token": token,
        "Origin": "Telegram",
    }
    payload = {"text": user_text}

    try:
        url = f"{API_GATEWAY_BASE_URL.rstrip('/')}/chat"
        resp = requests.post(url, json=payload, headers=headers, timeout=10, proxies={"http": None})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Ошибка при запросе /chat: {e}")
        await update.message.reply_text(
            "Ошибка связи с сервером. Попробуйте чуть позже."
        )
        return

    result_text = data.get("result_text", "")
    options = data.get("options", [])

    if result_text:
        pretty = json.dumps(result_text, ensure_ascii=False, indent=2)
        await update.message.reply_text(f"<pre>{pretty}</pre>", parse_mode="HTML")

    if options:
        keyboard = [[KeyboardButton(opt)] for opt in options]

    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(
        "Выберите вариант ответа:", reply_markup=reply_markup
    )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Извините, не понимаю эту команду.")


def main():
    init_db()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_FULLNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_fullname)
            ],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_INN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_inn)],
        },
        fallbacks=[CommandHandler("cancel", registration_cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("Бот запущен.")
    application.run_polling()


if __name__ == "__main__":
    main()
