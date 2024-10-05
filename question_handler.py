from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import add_question, add_assessment
from openai_api import get_questions_from_openai

# Функция для отправки следующего вопроса
async def send_next_question(update, context):
    questions = context.user_data.get('questions', [])
    current_question_index = context.user_data.get('current_question', 0)

    if current_question_index >= len(questions):
        await update.message.reply_text("Все вопросы были заданы!")
        await save_questions_to_database(update, context)
        return

    question = questions[current_question_index].strip()
    if question:
        await update.message.reply_text(f"Вопрос {current_question_index + 1}: {question}\nОцените этот вопрос от 1 до 5:")

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data='1')],
            [InlineKeyboardButton("2", callback_data='2')],
            [InlineKeyboardButton("3", callback_data='3')],
            [InlineKeyboardButton("4", callback_data='4')],
            [InlineKeyboardButton("5", callback_data='5')]
        ])

        await update.message.reply_text("Оцените этот вопрос:", reply_markup=reply_markup)

# Функция для генерации вопросов и отправки их пользователю
async def generate_and_send_questions(update, context):
    system_prompt = f"Ты нейро-экзаменатор. Твоя задача — генерировать {context.user_data['is_open']} вопросы для {context.user_data['prof']} уровня {context.user_data['level']} по технологии {context.user_data['technology']}."
    assistant_prompt = "Генерируй список вопросов."
    user_prompt = f"Пользователь выбрал {context.user_data['is_open']} вопросы."

    questions = await get_questions_from_openai(system_prompt, assistant_prompt, user_prompt)

    context.user_data['questions'] = questions.split("\n")
    context.user_data['current_question'] = 0
    context.user_data['evaluations'] = []
    await send_next_question(update, context)

# Функция для обработки оценки
async def handle_evaluation(update, context):
    query = update.callback_query
    await query.answer()

    rating = int(query.data)
    current_question_index = context.user_data.get('current_question', 0)
    context.user_data['evaluations'].append({
        'question': context.user_data['questions'][current_question_index],
        'rating': rating
    })

    context.user_data['current_question'] += 1
    await send_next_question(update, context)

# Сохранение в базу данных
async def save_questions_to_database(update, context):
    for evaluation in context.user_data['evaluations']:
        question_text = evaluation['question']
        rating = evaluation['rating']

        question_type_id = 1 if context.user_data['is_open'] == 'Открытые вопросы' else 2
        technology_id = context.user_data['technology']
        difficulty_id = context.user_data['level']

        question_id = add_question(update.effective_user.id, question_text, question_type_id, technology_id, difficulty_id)
        add_assessment(update.effective_user.id, question_id, rating, "")

    await update.message.reply_text("Все вопросы и оценки сохранены.")
