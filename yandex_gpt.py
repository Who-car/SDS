import json, re, time
from config import AUTH, FOLDER_ID, ASSISTANT_ID
from yandex_cloud_ml_sdk import YCloudML

assistant = None
sdk = YCloudML(folder_id=FOLDER_ID, auth=AUTH)
model = sdk.models.completions("yandexgpt-lite").configure(
    temperature=0.0, max_tokens=200
)
if ASSISTANT_ID:
    assistant = sdk.assistants.get(ASSISTANT_ID)
if not assistant:
    assistant = sdk.assistants.create(
        model, ttl_days=4, expiration_policy="since_last_active", max_tokens=500
    )

with open("metadata/categories.json", encoding="utf-8") as f:
        categories_meta: dict[str, str] = json.load(f)
        category_keys = list(categories_meta.keys())
        keys_str = ", ".join(category_keys)

PROMPT = """
Список категорий:
{categories}

Вы — ассистент. По входной строке пользовательского запроса сделайте семантический анализ и выделите:
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
system_rule=PROMPT.format(categories=keys_str)

def analyze_query(thread_id: str, query: str) -> tuple[dict, any]:
    start_time = time.time()

    thread = None
    if thread_id:
        thread = sdk.threads.get(thread_id)
        for message in thread:
            print(message.text)
    if not thread:
        print('thread not exists - creating...')
        thread = sdk.threads.create(
            name="SimpleAssistant", ttl_days=1, expiration_policy="static"
        )
        thread.write({"text": system_rule, "role": "USER"})
    
    thread.write(query)
    run = assistant.run(thread, custom_prompt_truncation_strategy="auto")
    result = run.wait()

    end_time = time.time()
    print(f"Время на обработку запроса: {end_time-start_time:.2f}с")
    print(f"Входные токены: {result.usage.input_text_tokens}, выходные токены: {result.usage.completion_tokens}, всего: {result.usage.total_tokens}")
    try:
        json_str = re.search(r"\{.*\}", result.message.parts[0], flags=re.DOTALL).group(0)
        output = json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        raise RuntimeError(
            f"Не удалось распарсить ответ модели: {e}\nОтвет модели: {result}"
        )
    return output, thread


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
