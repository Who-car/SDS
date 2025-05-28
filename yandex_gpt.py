import json, re, time, os
from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML

load_dotenv()
FOLDER_ID = os.getenv("FOLDER_ID")
AUTH = os.getenv("AUTH")

with open("metadata/categories.json", encoding="utf-8") as f:
    categories_meta: dict[str, str] = json.load(f)
    category_keys = list(categories_meta.keys())
    keys_str = ", ".join(category_keys)

sdk = YCloudML(folder_id=FOLDER_ID, auth=AUTH)

model = sdk.models.completions("yandexgpt").configure(temperature=0.0, max_tokens=300)

PROMPT = """
Список категорий:
{categories}

Вы — ассистент. По входной строке пользовательского запроса выделите:
1) категорию (один из списка выше)
2) артикулы (articles),
3) тип продукта (keys),
4) характеристики (characteristics) и их значения.

По блокам:
- include: всё, что явно запрашивается или упоминается без негатива;
- exclude: всё, что пользователь отрицательно исключает (любой «не», «без», а также сравнительные «не дороже X», «не менее Y» и т.п.).

Особые правила:
- Любые фразы с «не дороже», «не дороже чем», «не более», «не выше» → exclude (цена > X).
- Любые фразы с «не дешевле», «не менее», «минимум» → include (цена ≥ X).

Верните строго JSON в таком формате:

{{
  "category": "<название категории>"
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

Пользовательский запрос:
\"\"\"{query}\"\"\"
"""


def analyze_query(query: str) -> tuple[dict, any]:
    prompt = PROMPT.format(categories=keys_str, query=query.strip())
    response = model.run(prompt)
    try:
        json_str = re.search(r"\{.*\}", response.text, flags=re.DOTALL).group(0)
        output = json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        raise RuntimeError(
            f"Не удалось распарсить ответ модели: {e}\nОтвет модели: {response}"
        )
    return output, response.usage


if __name__ == "__main__":
    while True:
        user_query = input("Введите запрос: ")
        start_time = time.time()
        result, usage = analyze_query(user_query)
        end_time = time.time()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"Время на обработку запроса: {end_time - start_time:.2f}с.")
        print(usage)
        print()

# Какой сегодня замечательный день, не так ли?
# other__qtype

# Я хочу купить кабель категории 5e 300В синего цвета. Артикул 42-0037
# specified_product__qtype

# Хочу любой товар синего или зеленого цвета, но не дороже 500 рублей
# unclear_product_from_catalog__qtype

# Вы продаете часы?
# other__qtype

# Какие актуальные акции есть на сегодня?
# sales_info__qtype
