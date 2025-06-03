## Usage

Prerequisities: на машине должен быть установлен Python3

1. Добавить в корень проекта файл .env

2. Прописать в консоли следующие команды:
```
git clone https://github.com/Who-car/SDS.git sds-api
cd sds-api
pip install -r requirements.txt
python main.py 
```

3. Отправить login-запрос через Postman:
```
URL: http://localhost:8000/login
HTTP-method: POST
Body (json):
{
   "fullname": "user user user",
   "inn": "000000000000",
   "password": "999999",
   "phone": "89999999999"
}
```
В ответ возвращается token

4. Отправить запрос с текстом через Postman:
```
URL: http://localhost:8000/chat
HTTP-method: POST
Headers: {
    "Origin": "www.test.com",
    "Token": token
}
Body (json):
{
   "text": "Я хочу купить кабель категории 5e 300В синего цвета. Артикул 42-0037"
}
```
В ответ должен вернуться семантический анализ и ответ в формате json

## Updates

**01.06.26**: Добавлено логирование

**30.05.25**: Добавлена поддержка WebAPI и многопоточности, сокращено количество используемых токенов и время ответа до 3 секунд максимально

**28.05.25**: обновлен промт с учетом форматирования

## Примеры запросов

1. Пример WebAPI запроса

![web_api.png](img/web_api.png)