import json, re, time, os
from config import AUTH, FOLDER_ID, ASSISTANT_ID, SYSTEM_RULE, local_path
from yandex_cloud_ml_sdk import YCloudML

assistant = None
sdk = YCloudML(folder_id=FOLDER_ID, auth=AUTH)
model = sdk.models.completions("yandexgpt-lite").configure(
    temperature=0.0, max_tokens=200
)

sdk.setup_default_logging()

if ASSISTANT_ID:
    assistant = sdk.assistants.get(ASSISTANT_ID)
if not assistant:
    # files = []
    # for path in ["catalog.json"]:
    #     file = sdk.files.upload(
    #         local_path(path),
    #         ttl_days=5,
    #         expiration_policy="static",
    #     )
    #     files.append(file)

    # operation = sdk.search_indexes.create_deferred(files)
    # search_index = operation.wait()
    # tool = sdk.tools.search_index(search_index)
    assistant = sdk.assistants.create(
        model, ttl_days=4, expiration_policy="since_last_active", max_tokens=500
    )
    os.environ["ASSISTANT_ID"] = assistant.id


def analyze_query(thread_id: str, query: str) -> tuple[dict, any, any]:

    # TODO: добавить обновление треда
    # TODO: добавить обновление ассистента
    # TODO: добавить удаление тренда

    thread = None
    if thread_id:
        thread = sdk.threads.get(thread_id)
    if not thread:
        thread = sdk.threads.create(
            name="SimpleAssistant", ttl_days=1, expiration_policy="static"
        )
        thread.write({"text": SYSTEM_RULE, "role": "USER"})

    thread.write(query)
    run = assistant.run(thread, custom_prompt_truncation_strategy="auto")
    result = run.wait()

    try:
        json_str = re.search(r"\{.*\}", result.message.parts[0], flags=re.DOTALL).group(0)
        output = json.loads(json_str)
    except Exception as e:
        output = {"error": "Я не могу ответить на ваш вопрос"}
    return output, thread, result.usage
