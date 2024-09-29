from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from dotenv import load_dotenv
from promts import Promt
import os
from openai_api import get_questions_from_openai  # Импорт функции из openai_api.py

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TG_TOKEN')

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

# Функция для отображения первого набора кнопок
async def start(update: Update, context: CallbackContext):
    reply_markup = create_buttons(is_open_buttons)
    await update.message.reply_text('Выберите тип вопросов:', reply_markup=reply_markup)

# Функция для обработки нажатий кнопок
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Тип вопросов
    if query.data in is_open_buttons:
        context.user_data['params'] = f'{query.data}'
        reply_markup = create_buttons(prof_buttons)  # специальность
        await query.edit_message_text(text=f"Вы выбрали: {query.data}. Теперь выберите профессию:", reply_markup=reply_markup)

    # специальность
    elif query.data in prof_buttons:
        if query.data == "Разработчик":
            context.user_data['params'] += f', {query.data}'
            reply_markup = create_buttons(technology_buttons)  # технологии
            await query.edit_message_text(text=f"Вы выбрали: {query.data}. Теперь выберите технологию:", reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=f"Специальность: {query.data} пока в разработке")

    # технологии
    elif query.data in technology_buttons:
        context.user_data['params'] += f', {query.data}'
        reply_markup = create_buttons(level_buttons)  # уровни
        await query.edit_message_text(text=f"Ваш выбор: {query.data}.", reply_markup=reply_markup)

    # уровни
    elif query.data in level_buttons:
        context.user_data['params'] += f', {query.data}'
        await query.edit_message_text(text=f"Ваш выбор: {context.user_data['params']}. Генерирую вопросы...")

        # Вызов функции для генерации вопросов через OpenAI
        questions = await get_questions_from_openai(context.user_data['params'])
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
