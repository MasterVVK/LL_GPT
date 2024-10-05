from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import add_question, add_assessment
from openai_api import get_questions_from_openai

# Функция для отправки следующего вопроса
async def send_next_question(update, context):
    """Отправляем следующий вопрос пользователю"""
    questions = context.user_data.get('questions', [])
    current_question_index = context.user_data.get('current_question', 0)

    if current_question_index >= len(questions):
        await update.callback_query.message.reply_text("Все вопросы были заданы!")
        await save_questions_to_database(update, context)
        return

    question = questions[current_question_index].strip()
    if question:
        await update.callback_query.message.reply_text(f"Вопрос {current_question_index + 1}: {question}\nОцените этот вопрос от 1 до 5:")

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data='1')],
            [InlineKeyboardButton("2", callback_data='2')],
            [InlineKeyboardButton("3", callback_data='3')],
            [InlineKeyboardButton("4", callback_data='4')],
            [InlineKeyboardButton("5", callback_data='5')]
        ])

        await update.callback_query.message.reply_text("Оцените этот вопрос:", reply_markup=reply_markup)

# Функция для генерации вопросов и отправки их пользователю
async def generate_and_send_questions(update, context):
    """Генерация вопросов через OpenAI и отправка их пользователю"""
    system_prompt = f"Ты нейро-экзаменатор. Твоя задача — подготовить {context.user_data['is_open']} вопросы для {context.user_data['prof']} уровня {context.user_data['level']} по технологии {context.user_data['technology']}. Вопросы должны быть соответствующими, чтобы проверить знания и понимание специалиста.\n\nВопросы должны быть без нумерации. Каждый вопрос должен начинаться с ключевого слова 'Вопрос:' и быть в отдельной строке.\n\nНапример:\nВопрос: Какой у вас опыт работы с Python?\nВопрос: Объясните разницу между списками и кортежами в Python."

    assistant_prompt = "Генерируй список вопросов."
    user_prompt = f"Пользователь выбрал {context.user_data['is_open']} вопросы."

    # Вызов функции для генерации вопросов через OpenAI
    questions = await get_questions_from_openai(system_prompt, assistant_prompt, user_prompt)

    # Разбиваем полученный текст на вопросы, начиная с ключевого слова "Вопрос:"
    context.user_data['questions'] = [q.strip() for q in questions.split("\n") if q.startswith("Вопрос:")]
    context.user_data['current_question'] = 0  # Индекс текущего вопроса
    context.user_data['evaluations'] = []  # Список для хранения оценок
    await send_next_question(update, context)

# Функция для обработки оценки и перехода к следующему вопросу
async def handle_evaluation(update, context):
    """Обрабатываем оценку и переходим к следующему вопросу"""
    query = update.callback_query
    await query.answer()

    # Получаем оценку пользователя
    rating = int(query.data)

    # Сохраняем оценку для текущего вопроса
    current_question_index = context.user_data.get('current_question', 0)
    context.user_data['evaluations'].append({
        'question': context.user_data['questions'][current_question_index],
        'rating': rating
    })

    # Переходим к следующему вопросу
    context.user_data['current_question'] += 1
    await send_next_question(update, context)

# Функция для сохранения всех вопросов и оценок в базу данных
async def save_questions_to_database(update, context):
    """Сохраняем все вопросы и оценки в базу данных после завершения"""
    for evaluation in context.user_data['evaluations']:
        question_text = evaluation['question']
        rating = evaluation['rating']

        question_type_id = 1 if context.user_data['is_open'] == 'Открытые вопросы' else 2
        technology_id = context.user_data['technology']
        difficulty_id = context.user_data['level']

        question_id = add_question(update.effective_user.id, question_text, question_type_id, technology_id, difficulty_id)
        add_assessment(update.effective_user.id, question_id, rating, "")

    await update.callback_query.message.reply_text("Все вопросы и оценки сохранены.")
