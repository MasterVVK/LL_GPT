import os
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError
from dotenv import load_dotenv
import httpx

# Загрузка переменных окружения
load_dotenv()
OPENAI_API_KEY = os.getenv('GPT_SECRET_KEY')
PROXY_URL = os.getenv('PROXY_URL')  # Прокси-сервер

# Создаем кастомный HTTP-клиент с поддержкой прокси
http_client = httpx.AsyncClient(proxies=PROXY_URL)

# Инициализация асинхронного клиента OpenAI с кастомным HTTP-клиентом
client = AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

# Функция для взаимодействия с OpenAI API через прокси
async def get_questions_from_openai(system: str, assistant: str, user: str):
    try:
        # Используем новый метод chat.completions.create с асинхронным клиентом
        response = await client.chat.completions.create(
            model="gpt-4o",  # Используем модель gpt-4o
            messages=[
                {"role": "system", "content": system},
                {"role": "assistant", "content": assistant},
                {"role": "user", "content": user}
            ],
            temperature=0.1,
            max_tokens=500
        )

        # Возвращаем сгенерированный контент
        return response.choices[0].message.content

    # Обработка исключений API
    except APIError as e:
        return f"API Ошибка: {e}"
    except RateLimitError as e:
        return f"Превышен лимит запросов: {e}"
    except AuthenticationError as e:
        return f"Ошибка аутентификации: {e}"
    except APIConnectionError as e:
        return f"Ошибка соединения: {e}"
    except Exception as e:
        return f"Произошла общая ошибка: {str(e)}"

# Не забывайте закрывать асинхронный HTTP-клиент после работы
async def close_http_client():
    await http_client.aclose()
