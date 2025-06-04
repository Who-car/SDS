import os, json
from dotenv import load_dotenv

load_dotenv()

AUTH = os.getenv("AUTH")
FOLDER_ID = os.getenv("FOLDER_ID")
PORT = int(os.getenv("PORT"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_GATEWAY_BASE_URL = os.getenv("API_GATEWAY_BASE_URL")
PRODUCTS_MODULE_URL = os.getenv("PRODUCTS_MODULE_URL")
PRODUCT_TYPE = "specified_product__qtype"
LOG_PATH = "logs"
DB_PATH = f"{LOG_PATH}/app.db"
TG_PATH = f"{LOG_PATH}/telegram.db"
PROMPT = """
Список категорий:
{categories}

Вы — ассистент, который может отвечать на вопросы по товарам из каталога электротоваров.
Вы не умеете отвечать на вопросы по товарам не из каталога электротоваров. 
По входной строке пользовательского запроса сделайте семантический анализ и выделите:
1) категорию (один из списка выше),
2) намерение (intention),
3) артикулы (articles),
4) тип продукта (keys),
5) характеристики (characteristics) и их значения.

По блокам:
- include: всё, что явно запрашивается или упоминается без негатива;
- exclude: всё, что пользователь отрицательно исключает (любой «не», «без», а также сравнительные «не дороже X», «не менее Y» и т.п.).

Особые правила:
- Любые фразы с «не дороже», «не дороже чем», «не более», «не выше» → exclude (цена > X).
- Любые фразы с «не дешевле», «не менее», «минимум» → include (цена ≥ X).
- Намерение - это просто глагол. Не нужно добавлять сюда лишнюю информацию

Если категория = 'specified_product__qtype', то верните строго JSON в таком формате:

{{
  "category": "<название категории>",
  "намерение": "<намерение>",
  "include": {{
    "articles": [<список артикулов>],
    "keys": [<тип продукта>],
    "characteristics": {{
      "<Название1>": [<значение1>, <значение2>, ...],
      ...
    }}
  }},
  "exclude": {{
    "articles": [<список артикулов>],
    "keys": [<тип продукта>],
    "characteristics": {{
      "<НазваниеA>": [<значениеA1>, ...],
      ...
    }}
  }}
}}

В случае любой другой категории, верните JSON в таком формате:
{{
  "category": "<название категории>",
  "намерение": "<намерение>"
}}
"""


with open("metadata/categories.json", encoding="utf-8") as f:
    categories_meta: dict[str, str] = json.load(f)
    category_keys = list(categories_meta.keys())
    keys_str = ", ".join(category_keys)

SYSTEM_RULE = PROMPT.format(categories=keys_str)
