import pathlib, json, hashlib
from datetime import datetime
from rich import print as rprint
from repository import add_request, add_response


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def local_path(path: str) -> pathlib.Path:
    return pathlib.Path(__file__).parent / path

def log_request(request_id: str, user_id: str, token: str, source: str, query: str):
    preview = query[:50] + ("…" if len(query) > 50 else "")
    timestamp = datetime.now().strftime("%D.%M.%Y")

    add_request(request_id, user_id, token, source)
    rprint(
        f"[bold green]REQUEST[/bold green] "
        f"[white]id=[/white][cyan]{request_id}[/cyan] "
        f"[white]user=[/white][magenta]{user_id}[/magenta] "
        f"[white]src=[/white][green]{source or '-'}[/green] "
        f"[white]time=[/white][yellow]{timestamp}[/yellow] "
        f"[white]preview=[/white][grey62]{preview}[/grey62]"
    )

def log_context(request_id: str, user_id: str, response_obj: object, time: int, usage: any):
    response_json_str = json.dumps(response_obj, ensure_ascii=False)

    add_response(request_id, user_id, response_json_str)
    rprint(
        f"[bold blue]CONTEXT[/bold blue] "
        f"[white]id=[/white][cyan]{request_id}[/cyan] "
        f"[white]user=[/white][magenta]{user_id}[/magenta] "
        f"[white]response time=[/white][grey62]{time}s[/grey62] "
        f"[white]input tokens=[/white][grey62]{usage.input_text_tokens}[/grey62] "
        f"[white]output tokens=[/white][grey62]{usage.completion_tokens}[/grey62] "
        f"[white]total tokens=[/white][grey62]{usage.total_tokens}[/grey62]"
    )
