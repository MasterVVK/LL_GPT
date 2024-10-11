import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import create_connection, add_question, add_assessment
from openai_api import get_questions_from_openai

# Функция для чтения содержимого файла
def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
        return ""

# Функция для отправки следующего вопроса
async def send_next_question(update, context):
    """Отправляем следующий вопрос пользователю"""
    questions = context.user_data.get('questions', [])
    current_question_index = context.user_data.get('current_question', 0)

    # Проверяем, были ли все вопросы заданы
    if current_question_index >= len(questions):
        message = update.callback_query.message if update.callback_query else update.message
        await message.reply_text("Все вопросы были заданы!")
        return

    # Отправляем следующий вопрос
    question = questions[current_question_index].strip()
    if question:
        message = update.callback_query.message if update.callback_query else update.message
        await message.reply_text(f"Вопрос {current_question_index + 1}: {question}\nОцените этот вопрос от 1 до 5:")

        # Кнопки для оценки
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

    # Путь к папке с файлами промптов
    prompts_dir = "fastapi/Promts/"
    question_type = context.user_data['is_open']  # open или close

    # Чтение содержимого файлов с промптами
    system_prompt_template = read_file_content(os.path.join(prompts_dir, f"promt_system_{question_type}.txt"))
    assistant_prompt_template = read_file_content(os.path.join(prompts_dir, f"promt_assistant_{question_type}.txt"))
    user_prompt_template = read_file_content(os.path.join(prompts_dir, f"promt_user_{question_type}.txt"))

    # Подстановка данных пользователя в шаблоны
    system_prompt = system_prompt_template.format(
        question_type=context.user_data['is_open'],
        prof=context.user_data['prof'],
        level=context.user_data['level'],
        technology=context.user_data['technology']
    )

    assistant_prompt = assistant_prompt_template.format(
        question_type=context.user_data['is_open'],
        prof=context.user_data['prof'],
        level=context.user_data['level'],
        technology=context.user_data['technology']
    )

    user_prompt = user_prompt_template.format(
        question_type=context.user_data['is_open'],
        prof=context.user_data['prof'],
        level=context.user_data['level'],
        technology=context.user_data['technology'],
        num_questions=context.user_data['num_questions']
    )

    # Вызов функции для генерации вопросов через OpenAI API
    questions = await get_questions_from_openai(system_prompt, assistant_prompt, user_prompt)
    print(questions)

    # Разбиваем полученный текст на строки, считая каждую строку отдельным вопросом
    context.user_data['questions'] = [q.strip() for q in questions.split("\n") if q.strip()]

    # Проверяем, были ли сгенерированы вопросы
    if not context.user_data['questions']:
        await update.message.reply_text("Не удалось сгенерировать вопросы. Попробуйте снова.")
        return

    context.user_data['current_question'] = 0  # Индекс текущего вопроса
    context.user_data['evaluations'] = []  # Список для хранения оценок
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

    # Переходим к запросу комментария
    await query.message.reply_text("Пожалуйста, введите комментарий к этому вопросу:")

    # Устанавливаем состояние ожидания комментария
    context.user_data['awaiting_comment'] = True

# Функция для обработки комментария
async def handle_comment(update, context):
    """Обрабатываем комментарий и переходим к следующему вопросу"""
    if context.user_data.get('awaiting_comment', False):
        # Получаем комментарий от пользователя
        comment = update.message.text

        # Сохраняем комментарий для текущего вопроса
        current_question_index = context.user_data.get('current_question', 0)
        context.user_data['evaluations'][-1]['comment'] = comment

        # Попробуем сохранить оценку и комментарий в базу данных
        try:
            await save_evaluation_to_db(update, context)
            context.user_data['current_question'] += 1  # Переходим к следующему вопросу
            context.user_data['awaiting_comment'] = False  # Сбрасываем флаг комментария
            await send_next_question(update, context)  # Отправляем следующий вопрос
        except Exception as e:
            await update.message.reply_text(f"Ошибка при сохранении данных: {str(e)}")
    else:
        await update.message.reply_text("Оцените вопрос перед добавлением комментария.")

# Функция для сохранения данных в базу
async def save_evaluation_to_db(update, context):
    """Сохраняем текущий вопрос, оценку и комментарий в базу данных"""
    try:
        evaluation = context.user_data['evaluations'][-1]
        question_text = evaluation['question']
        rating = evaluation['rating']
        comment = evaluation.get('comment', "")

        question_type_id = 1 if context.user_data['is_open'] == 'Открытые вопросы' else 2
        technology_id = context.user_data['technology']
        difficulty_id = context.user_data['level']

        # Создаем подключение к базе данных
        conn = create_connection("project_database.db")
        if conn is not None:
            # Добавляем вопрос и сохраняем его идентификатор
            question_id = add_question(conn, question_text, question_type_id, technology_id, difficulty_id)

            # Добавляем оценку
            add_assessment(conn, update.effective_user.id, question_id, rating, comment)

            # Закрываем соединение с базой данных
            conn.close()
        else:
            raise Exception("Не удалось подключиться к базе данных")

    except Exception as e:
        raise Exception(f"Не удалось сохранить оценку и комментарий: {str(e)}")
