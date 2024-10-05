from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from dotenv import load_dotenv
from promts import Promt
import os
from openai_api import get_questions_from_openai  # Импорт функции из openai_api.py
from database import create_connection, add_user, create_tables  # Импорт функций для работы с БД

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TG_TOKEN')

# Путь к базе данных
DATABASE_PATH = "project_database.db"

# Опции для выбора в боте
is_open_buttons = ["Открытые вопросы", "Закрытые вопросы"]
prof_buttons = Promt.params_dict["prof"]
technology_buttons = Promt.params_dict["technology"]
level_buttons = Promt.params_dict["level"]

# Путь к папке с промптами
PROMPTS_DIR = "fastapi/Promts/"

# Функция для создания кнопок
def create_buttons(data_list):
    keyboard = []
    for item in data_list:
        keyboard.append([InlineKeyboardButton(item, callback_data=item)])
    return InlineKeyboardMarkup(keyboard)

# Функция для загрузки и редактирования промпта из файла
def load_and_edit_prompt(file_name, context_data):
    file_path = os.path.join(PROMPTS_DIR, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            prompt_content = file.read()

        # Заменяем плейсхолдеры в промпте на реальные данные
        prompt_content = prompt_content.replace("{prof}", context_data.get("prof", ""))
        prompt_content = prompt_content.replace("{technology}", context_data.get("technology", ""))
        prompt_content = prompt_content.replace("{level}", context_data.get("level", ""))
        prompt_content = prompt_content.replace("{question_type}", context_data.get("is_open", "").lower())

        return prompt_content
    except FileNotFoundError:
        return f"Файл {file_name} не найден."

# Функция для обработки команды /start
async def start(update: Update, context: CallbackContext):
    # Подключение к базе данных
    conn = create_connection(DATABASE_PATH)
    if conn is not None:
        create_tables(conn)  # Убедимся, что все таблицы созданы

        # Получаем информацию о пользователе
        user_id = update.effective_user.id
        username = update.effective_user.full_name
        email = ""  # Email может быть добавлен, если он доступен

        # Добавляем пользователя в базу данных
        add_user(conn, telegram_id=str(user_id), name=username, email=email)
        conn.close()

    reply_markup = create_buttons(is_open_buttons)
    await update.message.reply_text('Выберите тип вопросов:', reply_markup=reply_markup)

# Функция для обработки нажатий кнопок
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Тип вопросов (открытые или закрытые)
    if query.data in is_open_buttons:
        context.user_data['is_open'] = query.data  # Сохраняем тип вопроса (открытый или закрытый)
        reply_markup = create_buttons(prof_buttons)  # специальность
        await query.edit_message_text(text=f"Вы выбрали: {query.data}. Теперь выберите профессию:", reply_markup=reply_markup)

    # специальность
    elif query.data in prof_buttons:
        context.user_data['prof'] = query.data  # Сохраняем профессию
        if query.data == "Разработчик":
            reply_markup = create_buttons(technology_buttons)  # технологии
            await query.edit_message_text(text=f"Вы выбрали: {query.data}. Теперь выберите технологию:", reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=f"Специальность: {query.data} пока в разработке")

    # технологии
    elif query.data in technology_buttons:
        context.user_data['technology'] = query.data  # Сохраняем технологию
        reply_markup = create_buttons(level_buttons)  # уровни
        await query.edit_message_text(text=f"Вы выбрали технологию: {query.data}. Теперь выберите уровень:", reply_markup=reply_markup)

    # уровни
    elif query.data in level_buttons:
        context.user_data['level'] = query.data  # Сохраняем уровень
        await query.edit_message_text(text=f"Ваш выбор: {context.user_data}. Генерирую вопросы...")

        # Загружаем и редактируем промпты для system, assistant, user
        system_prompt = load_and_edit_prompt("promt_system.txt", context.user_data)
        assistant_prompt = load_and_edit_prompt("promt_assistant.txt", context.user_data)
        user_prompt = load_and_edit_prompt("promt_user.txt", context.user_data)

        # Вызов функции для генерации вопросов через OpenAI
        questions = await get_questions_from_openai(system_prompt, assistant_prompt, user_prompt)
        await query.edit_message_text(text=f"Сгенерированные вопросы:\n{questions}")

# Основная функция
def main() -> None:
    # создаем приложение и передаем в него токен
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд и кнопок
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
