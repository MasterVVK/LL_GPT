import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from dotenv import load_dotenv
from promts import Promt
from database import create_connection, add_user, create_tables, fill_base_tables
from question_handler import generate_and_send_questions, handle_evaluation  # Импорт функций из question_handler.py

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
def create_buttons(data_list):
    keyboard = []
    for item in data_list:
        keyboard.append([InlineKeyboardButton(item, callback_data=item)])
    return InlineKeyboardMarkup(keyboard)

# Функция для обработки команды /start
async def start(update: Update, context: CallbackContext):
    # Подключение к базе данных
    conn = create_connection(DATABASE_PATH)

    if conn is not None:
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

        # Вызов функции для генерации и отправки вопросов
        await generate_and_send_questions(update, context)

# Основная функция
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
    application.add_handler(CallbackQueryHandler(button))  # Обрабатывает выборы кнопок
    application.add_handler(CallbackQueryHandler(handle_evaluation))  # Обрабатывает оценку вопросов

    application.run_polling()

if __name__ == '__main__':
    main()
