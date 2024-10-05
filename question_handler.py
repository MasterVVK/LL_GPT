from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import add_question, add_assessment
from openai_api import get_questions_from_openai

# Функция для отправки следующего вопроса
async def send_next_question(update, context):
    """Отправляем следующий вопрос пользователю"""
    questions = context.user_data.get('questions', [])
    current_question_index = context.user_data.get('current_question', 0)

    # Проверяем, был ли это callback-запрос или команда
    message = update.callback_query.message if update.callback_query else update.message

    if current_question_index >= len(questions):
        await message.reply_text("Все вопросы были заданы!")
        return

    question = questions[current_question_index].strip()
    if question:
        await message.reply_text(f"Вопрос {current_question_index + 1}: {question}\nОцените этот вопрос от 1 до 5:")

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data='1')],
            [InlineKeyboardButton("2", callback_data='2')],
            [InlineKeyboardButton("3", callback_data='3')],
            [InlineKeyboardButton("4", callback_data='4')],
            [InlineKeyboardButton("5", callback_data='5')]
        ])

        await message.reply_text("Оцените этот вопрос:", reply_markup=reply_markup)

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
    print(system_prompt)
    print(questions)
    await send_next_question(update, context)

# Функция для обработки оценки
async def handle_evaluation(update, context):
    """Обрабатываем оценку и запрашиваем комментарий"""
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

    # Запрашиваем комментарий к вопросу
    await query.message.reply_text("Пожалуйста, введите комментарий к этому вопросу:")

    # Переход к состоянию ожидания комментария
    return "WAITING_FOR_COMMENT"

# Функция для обработки комментария
async def handle_comment(update, context):
    """Обрабатываем комментарий и переходим к следующему вопросу"""
    comment = update.message.text

    # Сохраняем комментарий для текущего вопроса
    current_question_index = context.user_data.get('current_question', 0)
    context.user_data['evaluations'][-1]['comment'] = comment

    # Сохраняем оценку и комментарий в базу данных
    await save_evaluation_to_db(update, context)

    # Переходим к следующему вопросу
    context.user_data['current_question'] += 1
    await send_next_question(update, context)

# Функция для сохранения данных в базу
async def save_evaluation_to_db(update, context):
    """Сохраняем текущий вопрос, оценку и комментарий в базу данных"""
    evaluation = context.user_data['evaluations'][-1]
    question_text = evaluation['question']
    rating = evaluation['rating']
    comment = evaluation.get('comment', "")

    question_type_id = 1 if context.user_data['is_open'] == 'Открытые вопросы' else 2
    technology_id = context.user_data['technology']
    difficulty_id = context.user_data['level']

    # Сохраняем вопрос и его оценку в базу данных
    question_id = add_question(update.effective_user.id, question_text, question_type_id, technology_id, difficulty_id)
    add_assessment(update.effective_user.id, question_id, rating, comment)
