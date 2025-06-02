from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
import uuid
import httpx

from dto import QueryRequest, QueryResponse
from chat_service import get_response
from utils import hash_password
from config import PRODUCT_TYPE, PRODUCTS_MODULE_URL
from repository import (
    init,
    get_user_by_token_id,
    get_thread_by_user,
    add_new_user,
    add_token,
    get_user_by_INN,
    get_token_by_user,
)
from validators import (
    validate_fullname,
    validate_password,
    validate_inn,
    validate_phone
)

# TODO: добавить вызов фиктивного метода (url - из конфига, тело - полученный запрос); Ожидаем в ответ какой-то json
# TODO: сделать тг-бота с:
# - отправкой регистрационной формы
# - сохранением токена где-то локально
# - отправкой запроса на этот модуль
# - показыванием options в виде кнопок


@asynccontextmanager
async def lifespan(app: FastAPI):
    init()
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/login")
async def login(request: Request):
    payload = await request.json()
    fullname = payload.get("fullname", "").strip()
    phone = payload.get("phone", "").strip()
    inn = payload.get("inn", "").strip()
    password = payload.get("password", "")

    validate_fullname(fullname)
    validate_phone(phone)
    validate_inn(inn)
    validate_password(password)

    password_hash = hash_password(password)

    user = get_user_by_INN(inn)
    if user:
        user_id = user.get("id")
        stored_hash = user.get("password_hash")
        if stored_hash != password_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        
        token = get_token_by_user(user_id)
        if not token:
            new_token = uuid.uuid4().hex
            add_token(user_id, new_token)
            return {"token": new_token}
        return {"token": token}
    else:
        user_id = add_new_user(
            fullname=fullname, INN=inn, phone=phone, password_hash=password_hash
        )
        new_token = uuid.uuid4().hex
        add_token(user_id, new_token)
        return {"token": new_token}


@app.post("/chat")
async def chat(req: QueryRequest, request: Request):
    request_id = uuid.uuid4().hex
    token = request.headers.get("token")
    origin = request.headers.get("origin", "")

    if not token:
        raise HTTPException(status_code=401, detail="Token header is missing.")

    user_id = get_user_by_token_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token.")

    thread_id = get_thread_by_user(user_id)

    try:
        response = await get_response(request_id, user_id, thread_id, req.text, token, origin)
        if getattr(response, "category", None) == PRODUCT_TYPE:
            async with httpx.AsyncClient() as client:
                external_resp = await client.get(
                    PRODUCTS_MODULE_URL,
                    json={
                        "source": origin,
                        "token": token,
                        "payload": response
                    }
                )

            if external_resp.status_code == 200:
                data = external_resp.json()
                result_text = data.get("result_text")
                options = data.get("options", [])
                return QueryResponse(result_text=result_text, options=options)
            else:
                return QueryResponse(result_text=external_resp.error, options=[])

        return QueryResponse(result_text=response, options=[])

    except Exception as e:
        print(e)
        return HTTPException(status_code=500, detail=str(e))
