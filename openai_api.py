import os
import openai
import aiohttp
from dotenv import load_dotenv

# Загрузка переменных окружения, включая OpenAI API ключ и прокси URL
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PROXY_URL = os.getenv('PROXY_URL')  # Прокси-сервер

# Устанавливаем API ключ
openai.api_key = OPENAI_API_KEY

# Функция для взаимодействия с OpenAI API через прокси
async def get_questions_from_openai(system: str, assistant: str, user: str):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    # Формируем сообщение для OpenAI на основе ролей system, assistant и user
    messages = [
        {"role": "system", "content": system},
        {"role": "assistant", "content": assistant},
        {"role": "user", "content": user}
    ]

    # Настраиваем payload для запроса
    payload = {
        "model": "gpt-4",  # Можно использовать gpt-3.5-turbo, если нужно
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 500
    }

    # Создаём сессию для работы через прокси-сервер с помощью aiohttp
    async with aiohttp.ClientSession() as session:
        try:
            # Делаем запрос через прокси-сервер
            async with session.post(url, headers=headers, json=payload, proxy=PROXY_URL) as response:
                if response.status == 200:
                    # Парсим и возвращаем результат
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"Ошибка при генерации вопросов: {response.status}"
        except Exception as e:
            return f"Произошла ошибка: {str(e)}"
