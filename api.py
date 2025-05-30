from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from yandex_gpt import analyze_query
import json

app = FastAPI()

class QueryRequest(BaseModel):
    user_id: str
    text: str

class QueryResponse(BaseModel):
    result: object

@app.on_event("startup")
def load_threads():
    global threads
    try:
        with open("metadata/users.json", encoding="utf-8") as f:
            threads = json.load(f)
    except FileNotFoundError:
        threads = {}


@app.on_event("shutdown")
def save_threads():
    with open("metadata/users.json", "w", encoding="utf-8") as f:
        json.dump(threads, f, ensure_ascii=False, indent=2)


@app.post("/chat", response_model=QueryResponse)
def chat(req: QueryRequest):
    thread_id = threads.get(req.user_id)
    try:
        response, thread = analyze_query(thread_id, req.text)
    except Exception as e:
        return HTTPException(500, detail=str(e))
    print(response)
    if (thread_id != thread.id):
        threads[req.user_id] = thread.id
    return QueryResponse(result=response)
