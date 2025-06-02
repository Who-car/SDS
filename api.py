from fastapi import FastAPI, HTTPException
from cachetools import TTLCache
from contextlib import asynccontextmanager
from pydantic import BaseModel
from yandex_gpt import analyze_query
from config import CACHE_TTL_SECONDS, CACHE_TTL_SIZE, USERS_PATH, log_context, log_request
from typing import Optional, Dict
import csv, os, uuid, time

threads = TTLCache(maxsize=CACHE_TTL_SIZE, ttl=CACHE_TTL_SECONDS)

class QueryRequest(BaseModel):
    user_id: str
    text: str

class QueryResponse(BaseModel):
    result: object


def load_user_threads(user_id=None) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    if not os.path.exists(USERS_PATH):
        return result

    with open(USERS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["id"]
            data = {
                "token": row.get("token", ""),
                "source": row.get("source", ""),
                "thread_id": row.get("thread_id", "")
            }
            if uid == user_id: return data
            result[uid] = data
        if user_id: return None
    return result


def save_user_threads(data: Dict[str, Dict[str, str]]):
    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
    with open(USERS_PATH, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "token", "source", "thread_id"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for uid, info in data.items():
            writer.writerow({
                "id": uid,
                "token": info.get("token", ""),
                "source": info.get("source", ""),
                "thread_id": info.get("thread_id", "")
            })   


@asynccontextmanager
async def lifespan(app: FastAPI):
    user_threads = load_user_threads()
    for user_id, info in user_threads.items():
        threads[user_id] = {
            "token": info.get("token", ""),
            "source": info.get("source", ""),
            "thread_id": info.get("thread_id", ""),
        }

    yield

    save_user_threads(dict(threads.items()))

app = FastAPI(lifespan=lifespan)

@app.post("/chat", response_model=QueryResponse)
async def chat(req: QueryRequest):
    request_id = str(uuid.uuid4())
    user_data: Optional[Dict[str, str]] = threads.get(req.user_id)

    if user_data is None:
        user_data = load_user_threads(req.user_id)
        if user_data is None:
            user_data = {"token": "", "source": "", "thread_id": ""}
        threads[req.user_id] = user_data

    thread_id = user_data.get("thread_id", "")

    log_request(request_id, req.user_id, "", req.text)

    try:
        start_time = time.time()
        response, thread, usage = analyze_query(thread_id, req.text)
        end_time = time.time()
    except Exception as e:
        return HTTPException(500, detail=str(e))

    # TODO: добавить проверку категории;

    if (thread_id != thread.id):
        user_data["thread_id"] = str(thread.id)
        threads[req.user_id] = user_data

    log_context(request_id, req.user_id, response, end_time-start_time, usage)

    return QueryResponse(result=response)
