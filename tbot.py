from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, Updater, CommandHandler, CallbackQueryHandler, CallbackContext, ContextTypes
from dotenv import load_dotenv
from promts import Promt
import os


# подгружаем переменные окружения
load_dotenv()

# токен бота
TOKEN = os.getenv('TG_TOKEN')

is_open_buttons = ["Открытые вопросы", "Закрытые вопросы"]
prof_buttons = Promt.params_dict["prof"]
technology_buttons = Promt.params_dict["technology"]
level_buttons = Promt.params_dict["level"]


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
        reply_markup = create_buttons(prof_buttons) #специальность
        await query.edit_message_text(text=f"Вы выбрали: {query.data}. Теперь выберите профессию:", reply_markup=reply_markup)

    # специальность
    elif query.data in prof_buttons:
        if query.data == "Разработчик":
            context.user_data['params'] += f', {query.data}' 
            reply_markup = create_buttons(technology_buttons) # технологии 
            await query.edit_message_text(text=f"Вы выбрали: {query.data}. Теперь выберете технологию:", reply_markup=reply_markup)
        else: 
            await query.edit_message_text(text=f"Специальность: {query.data} пока в разработке")
             
    # технологии         
    elif query.data in technology_buttons:    
        context.user_data['params'] += f', {query.data}' 
        reply_markup = create_buttons(level_buttons) # технологии   
        await query.edit_message_text(text=f"Ваш выбор: {query.data}.", reply_markup=reply_markup)
                
    # уровни
    elif query.data in level_buttons:    
        context.user_data['params'] += f', {query.data}'  
        await query.edit_message_text(text=f"Ваш выбор: {context.user_data['params']}", reply_markup="")    

    await query.answer()  
      
  

    
# Основная функция
def main() -> None:
 
  # создаем приложение и передаем в него токен
    application = Application.builder().token(TOKEN).build()
    print('Бот запущен...')


    # Регистрируем обработчики команд и кнопок
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    
    application.run_polling()
    print('Бот остановлен')

if __name__ == '__main__':
    main()
