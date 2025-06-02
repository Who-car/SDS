import os, json, pathlib, csv
from datetime import datetime
from dotenv import load_dotenv
from rich import print as rprint

load_dotenv()


def local_path(path: str) -> pathlib.Path:
    return pathlib.Path(__file__).parent / path


AUTH = os.getenv("AUTH")
FOLDER_ID = os.getenv("FOLDER_ID")
PORT = int(os.getenv("PORT"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_TTL_SIZE = 10_000
LOG_PATH = "logs"
USERS_PATH = f"{LOG_PATH}/users.csv"
REQUESTS_PATH = f"{LOG_PATH}/requests.csv"
CONTEXT_PATH = f"{LOG_PATH}/context.csv"

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


def log_request(request_id: str, user_id: str, source: str, query: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "request_id": request_id,
        "user_id": user_id,
        "source": source,
        "timestamp": timestamp,
        "status": "Новый",
    }

    with open(REQUESTS_PATH, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["request_id", "user_id", "source", "timestamp", "status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not os.path.exists(REQUESTS_PATH):
            writer.writeheader()
        writer.writerow(row)

    preview = query[:50] + ("…" if len(query) > 50 else "")
    rprint(
        f"[bold green]REQUEST[/bold green] "
        f"[white]id=[/white][cyan]{request_id}[/cyan] "
        f"[white]user=[/white][magenta]{user_id}[/magenta] "
        f"[white]src=[/white][green]{source or '-'}[/green] "
        f"[white]time=[/white][yellow]{timestamp}[/yellow] "
        f"[white]preview=[/white][grey62]{preview}[/grey62]"
    )


def log_context(
    request_id: str, user_id: str, response_obj: object, time: int, usage: any
):
    response_json_str = json.dumps(response_obj, ensure_ascii=False)
    row = {
        "request_id": request_id,
        "user_id": user_id,
        "response_json": response_json_str,
    }

    with open(CONTEXT_PATH, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["request_id", "user_id", "response_json"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not os.path.exists(CONTEXT_PATH):
            writer.writeheader()
        writer.writerow(row)
    rprint(
        f"[bold blue]CONTEXT[/bold blue] "
        f"[white]id=[/white][cyan]{request_id}[/cyan] "
        f"[white]user=[/white][magenta]{user_id}[/magenta] "
        f"[white]response time=[/white][grey62]{time}s[/grey62] "
        f"[white]input tokens=[/white][grey62]{usage.input_text_tokens}[/grey62] "
        f"[white]output tokens=[/white][grey62]{usage.completion_tokens}[/grey62] "
        f"[white]total tokens=[/white][grey62]{usage.total_tokens}[/grey62]"
    )
