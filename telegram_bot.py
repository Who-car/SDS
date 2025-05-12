import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, filters
from langchain_community.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
import json, re, requests, os
from indexer import Indexer

ASK_QUERY, HANDLE_CATEGORY, HANDLE_PRODUCT = range(3)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
API_BASE_URL = 'http://193.106.69.207:8760/rexant/hs/api/v1'

model_path = "model/vicuna-7b-v1.5.Q4_K_M.gguf"
threshold_increment = 0.25
llm = LlamaCpp(
    model_path=model_path,
    n_ctx=2048,
    n_threads=6,
    f16_kv=True,
    verbose=False,
    temperature=0.05,
    top_p=0.3,
    max_tokens=200,
    echo=False,
    use_mlock=True
)
clarify_template = PromptTemplate(
    input_variables=["options"],
    template=(
        "У пользователя есть несколько вариантов: {options}."
        " Выбери одну ключевую характеристику, которая лучше всего разделяет эти варианты (например, 'тип', 'цвет' или 'размер')."
        " Сформулируй короткий нейтральный вопрос."
        " Ответь **строго** в формате JSON с двумя полями: 'question' (строка) и 'options' (массив строк), без дополнительного текста или пояснений."
        "**никакого форматирования, первый и последний символ твоего ответа - фигурные скобки**"
        " Пример правильного ответа: {{\"question\": \"Какой тип кабеля вас интересует?\", \"options\": [\"Витая пара\", \"Оптический кабель\"]}}"
    )
)

index = Indexer()

def get_restart_keyboard():
    keyboard = [[InlineKeyboardButton('Начать заново', callback_data='restart')]]
    return InlineKeyboardMarkup(keyboard)

async def disambiguate_options(options, context):
    opts_str = ", ".join(options)
    llm_prompt = clarify_template.format(options=opts_str)
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, llm.predict, llm_prompt)
    context.user_data['current_task'] = future
    try:
        response = await future
    except asyncio.CancelledError:
        return {"question": "Какой вариант вам подходит?", "options": options}
    finally:
        context.user_data.pop('current_task', None)
    json_match = re.search(r"\{.*\}", response, flags=re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    return {"question": "Какой вариант вам подходит?", "options": options}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    task = context.user_data.pop('current_task', None)
    if task and not task.done():
        task.cancel()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Чем могу помочь?")
    context.user_data['threshold'] = 0.75
    context.user_data['memory'] = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    return ASK_QUERY

async def handle_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.user_data['query'] = None
    task = context.user_data.pop('current_task', None)
    if task and not task.done():
        task.cancel()
    return await start(update, context)

async def ask_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = context.user_data.get('query', update.message.text)

    context.user_data['memory'].clear()
    context.user_data['memory'].save_context({"input": query}, {"output": ""})
    await update.message.reply_text("Идет поиск категорий...", reply_markup=get_restart_keyboard())
    results = index.search_catalog(query, context.user_data['threshold'])
    if not results:
        await update.message.reply_text(
            "Ничего не найдено, попробуйте изменить запрос.", reply_markup=get_restart_keyboard()
        )
        return ASK_QUERY
    if len(results) == 1:
        context.user_data['category'] = results[0].metadata.get('name')
        return await start_product_search(update, context)
    titles = [r.metadata.get('name', str(r)) for r in results]
    clarif = await disambiguate_options(titles, context)
    context.user_data['clarif_opts'] = clarif['options']
    context.user_data['options_results'] = results
    keyboard = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(clarif['options'])]
    await update.message.reply_text(
        clarif['question'], reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return HANDLE_CATEGORY

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    threshold = context.user_data['threshold']
    choice = int(update.callback_query.data)
    await update.callback_query.answer()
    selected = context.user_data['clarif_opts'][choice]
    context.user_data['memory'].save_context({"input": selected}, {"output": ""})
    context.user_data['threshold'] = threshold + threshold_increment
    context.user_data['query'] = selected
    return await ask_catalog(update.callback_query, context)

async def start_product_search(update_src: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_history = " ".join([m.content for m in context.user_data['memory'].load_memory_variables({})['chat_history']])
    context.user_data['memory'].save_context({"input": chat_history}, {"output": ""})
    await update_src.message.reply_text("Идет поиск товаров...", reply_markup=get_restart_keyboard())
    results = index.search_product(chat_history, 0.72)
    if not results:
        await update_src.message.reply_text(
            "Извините, по вашему запросу ничего не найдено.", reply_markup=get_restart_keyboard()
        )
        return ConversationHandler.END
    if len(results) == 1:
        prod = results[0]
        resp = requests.get(
            f"{API_BASE_URL}/photo?productid={prod.metadata['productid']}",
            headers={"Authorization": f"Token {AUTH_TOKEN}"}
        )
        caption = (
            f"Найденный товар:\nАртикул: {prod.metadata['article']}\n"
            f"Название: {prod.metadata['name']}\nОписание: {prod.metadata['description'][:150]}..."
        )
        if resp.status_code == 200:
            photo_url = resp.json().get("result").get("results")[0].get("filelink")
            await context.bot.send_photo(
                chat_id=update_src.effective_chat.id,
                photo=photo_url,
                caption=caption,
                reply_markup=get_restart_keyboard()
            )
        else:
            await update_src.message.reply_text(caption, reply_markup=get_restart_keyboard())
        return ConversationHandler.END
    titles = [r.metadata.get('name', str(r)) for r in results]
    clarif = await disambiguate_options(titles, context)
    context.user_data['clarif_opts'] = clarif['options']
    context.user_data['prod_results'] = results
    keyboard = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(clarif['options'])]
    await update_src.message.reply_text(
        clarif['question'], reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return HANDLE_PRODUCT

async def handle_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = int(update.callback_query.data)
    await update.callback_query.answer()
    prod = context.user_data['prod_results'][choice]
    resp = requests.get(
        f"{API_BASE_URL}/photo?productid={prod.metadata['productid']}",
        headers={"Authorization": f"Token {AUTH_TOKEN}"}
    )
    caption = (
        f"Найденный товар:\nАртикул: {prod.metadata['article']}\n"
        f"Название: {prod.metadata['name']}\nОписание: {prod.metadata['description'][:150]}..."
    )
    if resp.status_code == 200:
        photo_url = resp.json().get("result").get("results")[0].get("filelink")
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_url,
            caption=caption,
            reply_markup=get_restart_keyboard()
        )
    else:
        await update.reply_text(caption, reply_markup=get_restart_keyboard())
    return ConversationHandler.END

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_catalog)],
            HANDLE_CATEGORY: [CallbackQueryHandler(handle_category)],
            HANDLE_PRODUCT: [CallbackQueryHandler(handle_product)],
        },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(handle_restart, pattern='^restart$')]
    )
    app.add_handler(conv_handler)
    app.run_polling()
