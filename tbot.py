import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
from promts import Promt
from database import create_connection, add_user, create_tables, fill_base_tables
from question_handler import generate_and_send_questions, handle_evaluation, handle_comment, handle_answer_block_evaluation, handle_answer_block_comment

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

# Функция для создания кнопок
def create_buttons(data_list, prefix=""):
    keyboard = []
    for item in data_list:
        callback_data = f"{prefix}{item}"  # Добавляем префикс к callback_data
        keyboard.append([InlineKeyboardButton(item, callback_data=callback_data)])
    return InlineKeyboardMarkup(keyboard)

# Функция для обработки команды /start
async def start(update: Update, context: CallbackContext):
    # Очищаем данные пользователя при повторном вызове /start
    context.user_data.clear()

    # Подключение к базе данных
    conn = create_connection(DATABASE_PATH)

    if conn is not None:
        # Получаем информацию о пользователе
        user_id = update.effective_user.id
        username = update.effective_user.full_name
        email = update.effective_user.id  # Email может быть добавлен, если он доступен

        # Добавляем пользователя в базу данных
        add_user(conn, telegram_id=str(user_id), name=username, email=email)
        conn.close()

    # Создаем кнопки для выбора типа вопросов (без префикса)
    reply_markup = create_buttons(is_open_buttons)
    await update.message.reply_text('Выберите тип вопросов:', reply_markup=reply_markup)

# Функция для обработки нажатий кнопок
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Обрабатываем выбор типа вопросов (открытые или закрытые)
    if query.data.startswith("Открытые вопросы") or query.data.startswith("Закрытые вопросы"):
        # Сохраняем тип вопросов и добавляем его в context.user_data
        context.user_data['is_open'] = "open" if query.data == "Открытые вопросы" else "close"

        # Переходим к следующему шагу — выбор профессии
        reply_markup = create_buttons(prof_buttons, "prof_")
        await query.edit_message_text(text="Теперь выберите профессию:", reply_markup=reply_markup)

    # Обрабатываем выбор профессии
    elif query.data.startswith("prof_"):
        query_data = query.data[5:]  # Получаем профессию из callback data
        context.user_data['prof'] = query_data  # Сохраняем профессию
        # Переходим к выбору технологии
        reply_markup = create_buttons(technology_buttons, "tech_")
        await query.edit_message_text(text=f"Вы выбрали профессию: {query_data}. Теперь выберите технологию:", reply_markup=reply_markup)

    # Обрабатываем выбор технологии
    elif query.data.startswith("tech_"):
        query_data = query.data[5:]  # Получаем технологию из callback data
        context.user_data['technology'] = query_data  # Сохраняем технологию
        # Переходим к выбору уровня
        reply_markup = create_buttons(level_buttons, "level_")
        await query.edit_message_text(text=f"Вы выбрали технологию: {query_data}. Теперь выберите уровень:", reply_markup=reply_markup)

    # Обрабатываем выбор уровня
    elif query.data.startswith("level_"):
        query_data = query.data[6:]  # Получаем уровень из callback data
        context.user_data['level'] = query_data  # Сохраняем уровень
        await query.edit_message_text(text=f"Ваш выбор: {context.user_data}. Генерирую вопросы...")

        # Вызов функции для генерации и отправки вопросов
        await generate_and_send_questions(update, context)

# Основная функция запуска бота
def main() -> None:
    # создаем приложение и передаем в него токен
    application = Application.builder().token(TOKEN).build()

    # Подключение к базе данных и заполнение таблиц при старте бота
    conn = create_connection(DATABASE_PATH)
    if conn is not None:
        create_tables(conn)  # Создаем таблицы, если их нет
        fill_base_tables(conn)  # Заполняем таблицы данными
        conn.close()

    # Регистрируем обработчики команд и кнопок
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button, pattern='^(Открытые вопросы|Закрытые вопросы|prof_|tech_|level_)'))  # Обрабатывает выборы кнопок
    application.add_handler(CallbackQueryHandler(handle_evaluation, pattern='^(open|close_question)_([1-5])$'))  # Обрабатывает оценку вопросов
    application.add_handler(CallbackQueryHandler(handle_answer_block_evaluation, pattern='^(close_block)_([1-5])$'))  # Оценка блока ответов
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_comment))  # Обрабатывает комментарии
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer_block_comment))  # Обрабатывает комментарии к блоку ответов

    application.run_polling()

if __name__ == '__main__':
    main()
