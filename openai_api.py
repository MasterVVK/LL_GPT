import os
import openai
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PROXY_URL = os.getenv('PROXY_URL')  # Прокси-сервер

# Устанавливаем API ключ для OpenAI
openai.api_key = OPENAI_API_KEY

# Настройка прокси через OpenAI SDK
openai.proxy = {"http": PROXY_URL, "https": PROXY_URL}

# Функция для взаимодействия с OpenAI API через прокси
async def get_questions_from_openai(system: str, assistant: str, user: str):
    try:
        # Используем новый метод из OpenAI API (новая версия библиотеки)
        response = openai.chat.create(
            model="gpt-4o",  # Используем новую модель gpt-4o
            messages=[
                {"role": "system", "content": system},
                {"role": "assistant", "content": assistant},
                {"role": "user", "content": user}
            ],
            temperature=0.1,
            max_tokens=500
        )

        # Возвращаем сгенерированный контент
        return response.choices[0]['message']['content']

    # Обработка ошибок API
    except openai.error.APIError as e:
        return f"API Ошибка: {e}"
    except openai.error.RateLimitError as e:
        return f"Превышен лимит запросов: {e}"
    except openai.error.AuthenticationError as e:
        return f"Ошибка аутентификации: {e}"
    except openai.error.InvalidRequestError as e:
        return f"Неверный запрос: {e}"
    except Exception as e:
        return f"Произошла общая ошибка: {str(e)}"
