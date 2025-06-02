import time
from utils import log_request, log_context
from yandex_gpt import analyze_query
from repository import update_thread_for_user

async def get_response(request_id, user_id, thread_id, query, token, origin):
    log_request(request_id, user_id, token, origin, query)

    start_time = time.time()
    response, thread, usage = await analyze_query(thread_id, query)
    end_time = time.time()

    log_context(request_id, user_id, response, end_time - start_time, usage)

    if thread_id != thread.id:
        update_thread_for_user(user_id, thread.id)

    return response
