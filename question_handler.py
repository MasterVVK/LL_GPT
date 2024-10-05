import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import create_connection, add_question, add_assessment
from openai_api import get_questions_from_openai

# Устанавливаем уровень логирования для вывода в консоль
logging.basicConfig(level=logging.INFO)


# Функция для отправки следующего вопроса
async def send_next_question(update, context):
    """Отправляем следующий вопрос пользователю"""
    questions = context.user_data.get('questions', [])
    current_question_index = context.user_data.get('current_question', 0)

    # Проверяем, были ли все вопросы заданы
    if current_question_index >= len(questions):
        # Проверяем, был ли это callback-запрос или команда
        message = update.callback_query.message if update.callback_query else update.message
        await message.reply_text("Все вопросы были заданы!")
        logging.info("Все вопросы были заданы.")
        return

    # Отправляем следующий вопрос
    question = questions[current_question_index].strip()
    if question:
        # Проверяем, был ли это callback-запрос или команда
        message = update.callback_query.message if update.callback_query else update.message
        await message.reply_text(f"Вопрос {current_question_index + 1}: {question}\nОцените этот вопрос от 1 до 5:")

        # Логируем отправку вопроса
        logging.info(f"Отправлен вопрос {current_question_index + 1}: {question}")

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
    system_prompt = f"Ты экзаменатор на собеседовании. Твоя задача — подготовить вопросы для собеседования на позицию {context.user_data['prof']} с уровнем {context.user_data['level']} по технологии {context.user_data['technology']}."

    assistant_prompt = "Генерируй список вопросов."
    user_prompt = f"Пользователь выбрал {context.user_data['is_open']} вопросы."

    # Вызов функции для генерации вопросов через OpenAI
    questions = await get_questions_from_openai(system_prompt, assistant_prompt, user_prompt)

    # Разбиваем полученный текст на строки, считая каждую строку отдельным вопросом
    context.user_data['questions'] = [q.strip() for q in questions.split("\n") if q.strip()]

    # Проверяем, были ли сгенерированы вопросы
    if not context.user_data['questions']:
        await update.message.reply_text("Не удалось сгенерировать вопросы. Попробуйте снова.")
        logging.info("Не удалось сгенерировать вопросы.")
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

    # Логируем информацию о нажатой кнопке
    logging.info(f"Нажата кнопка: {rating}")

    # Сохраняем оценку для текущего вопроса
    current_question_index = context.user_data.get('current_question', 0)
    logging.info(f"Текущий вопрос: {current_question_index}")

    context.user_data['evaluations'].append({
        'question': context.user_data['questions'][current_question_index],
        'rating': rating
    })

    # Логируем переход к запросу комментария
    logging.info("Запрашиваем комментарий от пользователя.")

    # Переходим к запросу комментария
    await query.message.reply_text("Пожалуйста, введите комментарий к этому вопросу:")

    # Устанавливаем состояние ожидания комментария
    context.user_data['awaiting_comment'] = True
    logging.info("Ожидание комментария от пользователя установлено.")


# Функция для обработки комментария
async def handle_comment(update, context):
    """Обрабатываем комментарий и переходим к следующему вопросу"""
    if context.user_data.get('awaiting_comment', False):
        # Получаем комментарий от пользователя
        comment = update.message.text

        # Логируем полученный комментарий
        logging.info(f"Комментарий пользователя: {comment}")

        # Сохраняем комментарий для текущего вопроса
        current_question_index = context.user_data.get('current_question', 0)
        context.user_data['evaluations'][-1]['comment'] = comment

        # Попробуем сохранить оценку и комментарий в базу данных
        try:
            logging.info(f"Сохраняем данные для вопроса {current_question_index}")
            await save_evaluation_to_db(update, context)

            # Переходим к следующему вопросу
            context.user_data['current_question'] += 1
            logging.info(
                f"Переход к следующему вопросу. Текущий индекс вопроса: {context.user_data['current_question']}")

            context.user_data['awaiting_comment'] = False  # Сбрасываем флаг комментария
            await send_next_question(update, context)  # Отправляем следующий вопрос
        except Exception as e:
            logging.error(f"Ошибка при сохранении данных: {str(e)}")
            await update.message.reply_text(f"Ошибка при сохранении данных: {str(e)}")
    else:
        logging.info("Не удалось получить комментарий, поскольку оценка вопроса не была сделана.")
        await update.message.reply_text("Оцените вопрос перед добавлением комментария.")


# Функция для сохранения данных в базу
async def save_evaluation_to_db(update, context):
    """Сохраняем текущий вопрос, оценку и комментарий в базу данных"""
    try:
        # Получаем данные из контекста
        evaluation = context.user_data['evaluations'][-1]
        question_text = evaluation['question']
        rating = evaluation['rating']
        comment = evaluation.get('comment', "")

        # Получаем параметры для записи
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
        logging.error(f"Не удалось сохранить оценку и комментарий: {str(e)}")
        raise Exception(f"Не удалось сохранить оценку и комментарий: {str(e)}")
