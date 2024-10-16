import os
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import create_connection, add_question, add_assessment, add_answer, add_answer_assessment
from openai_api import get_questions_from_openai
from promts import Promt


# Функция для чтения содержимого файла
def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
        return ""


# Функция для парсинга закрытых вопросов с вариантами ответов
def parse_generated_questions(generated_text):
    """
    Парсинг сгенерированных вопросов, вариантов ответов и правильного ответа.
    Возвращает список вопросов с вариантами ответов.
    """
    questions = []
    pattern = r"Вопрос: (.*?)\nВарианты ответов:\n(?:a\) (.*?)\n)?(?:b\) (.*?)\n)?(?:c\) (.*?)\n)?(?:d\) (.*?)\n)?Правильный ответ: (\w)"

    matches = re.findall(pattern, generated_text)

    for match in matches:
        question = {
            'text': match[0],
            'options': [match[1], match[2], match[3], match[4]],
            'correct': match[5]  # Например, "a", "b", "c" или "d"
        }
        questions.append(question)

    return questions


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

    # Определяем переменную message
    message = update.message if update.message else update.callback_query.message

    # Получаем текущий вопрос
    question = questions[current_question_index]

    # Если это закрытые вопросы, отправляем варианты ответов
    if context.user_data['is_open'] == "close":
        await message.reply_text(f"Вопрос {current_question_index + 1}: {question['text']}\n"
                                 f"Варианты ответов:\n"
                                 f"a) {question['options'][0]}\n"
                                 f"b) {question['options'][1]}\n"
                                 f"c) {question['options'][2]}\n"
                                 f"d) {question['options'][3]}\n"
                                 f"\nПравильный ответ: {question['correct']}")

        # Оценка закрытого вопроса
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data='close_question_1')],
            [InlineKeyboardButton("2", callback_data='close_question_2')],
            [InlineKeyboardButton("3", callback_data='close_question_3')],
            [InlineKeyboardButton("4", callback_data='close_question_4')],
            [InlineKeyboardButton("5", callback_data='close_question_5')]
        ])
        await message.reply_text("Оцените закрытый вопрос:", reply_markup=reply_markup)
    else:
        # Для открытых вопросов просто отправляем текст и просим оценку
        await message.reply_text(f"Вопрос {current_question_index + 1}: {question.strip()}")

        # Оценка для открытых вопросов
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data='open_1')],
            [InlineKeyboardButton("2", callback_data='open_2')],
            [InlineKeyboardButton("3", callback_data='open_3')],
            [InlineKeyboardButton("4", callback_data='open_4')],
            [InlineKeyboardButton("5", callback_data='open_5')]
        ])
        await message.reply_text("Оцените этот вопрос:", reply_markup=reply_markup)


# Функция для генерации вопросов и отправки их пользователю
async def generate_and_send_questions(update, context):
    """Генерация вопросов через OpenAI и отправка их пользователю"""

    # Путь к папке с файлами промптов
    prompts_dir = "fastapi/Promts/"
    question_type = context.user_data['is_open']  # open или close
    num_questions = Promt.params_dict["num_questions"]

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
        num_questions=num_questions
    )

    # Вызов функции для генерации вопросов через OpenAI API
    questions = await get_questions_from_openai(system_prompt, assistant_prompt, user_prompt)
    print(questions)

    # Если тип вопроса закрытый, используем парсинг для вариантов ответов
    if context.user_data['is_open'] == "close":
        context.user_data['questions'] = parse_generated_questions(questions)
    else:
        # Для открытых вопросов просто сохраняем текст
        context.user_data['questions'] = [q.strip() for q in questions.split("\n") if q.strip()]

    # Проверяем, были ли сгенерированы вопросы
    if not context.user_data['questions']:
        message = update.message if update.message else update.callback_query.message
        await message.reply_text("Не удалось сгенерировать вопросы. Попробуйте снова.")
        return

    context.user_data['current_question'] = 0  # Индекс текущего вопроса
    context.user_data['evaluations'] = []  # Список для хранения оценок
    await send_next_question(update, context)


# Функция для обработки оценки
async def handle_evaluation(update, context):
    """Обрабатываем оценку и запрашиваем комментарий"""
    query = update.callback_query
    await query.answer()

    # Определяем, это оценка открытого вопроса, закрытого вопроса или блока ответов закрытого вопроса
    if query.data.startswith("open_"):
        # Это оценка открытого вопроса
        rating = int(query.data.split("_")[1])

        # Сохраняем оценку для текущего открытого вопроса
        current_question_index = context.user_data.get('current_question', 0)
        context.user_data['evaluations'].append({
            'question': context.user_data['questions'][current_question_index],
            'rating': rating
        })

        # Переходим к запросу комментария для открытого вопроса
        await query.message.reply_text("Пожалуйста, введите комментарий к этому вопросу:")
        context.user_data['awaiting_comment'] = True

    elif query.data.startswith("close_question_"):
        # Это оценка закрытого вопроса
        rating = int(query.data.split("_")[2])

        # Сохраняем оценку закрытого вопроса
        current_question_index = context.user_data.get('current_question', 0)
        context.user_data['evaluations'].append({
            'question': context.user_data['questions'][current_question_index],
            'rating': rating
        })

        # Переходим к запросу комментария для закрытого вопроса
        await query.message.reply_text("Пожалуйста, введите комментарий к закрытому вопросу:")
        context.user_data['awaiting_comment'] = True

    elif query.data.startswith("close_block_"):
        # Это оценка блока ответов закрытого вопроса
        rating = int(query.data.split("_")[2])

        # Сохраняем оценку блока ответов
        current_question_index = context.user_data.get('current_question', 0)
        context.user_data['evaluations'][-1]['answer_block_rating'] = rating

        # Переходим к запросу комментария к блоку ответов
        await query.message.reply_text("Пожалуйста, введите комментарий к блоку ответов:")
        context.user_data['awaiting_answer_block_comment'] = True


# Функция для обработки комментария к вопросу
async def handle_comment(update, context):
    """Обрабатываем комментарий к вопросу и проверяем тип вопроса"""
    if context.user_data.get('awaiting_comment', False):
        # Получаем комментарий от пользователя
        comment = update.message.text

        # Сохраняем комментарий для текущего вопроса
        current_question_index = context.user_data.get('current_question', 0)
        context.user_data['evaluations'][-1]['comment'] = comment

        # Сбрасываем флаг ожидания комментария
        context.user_data['awaiting_comment'] = False

        # Проверяем, закрытый это вопрос или открытый
        if context.user_data['is_open'] == "close":
            # Переходим к оценке блока ответов для закрытых вопросов
            await update.message.reply_text("Комментарий сохранен. Теперь оцените блок ответов.")

            # Кнопки для оценки блока ответов
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("1", callback_data='close_block_1')],
                [InlineKeyboardButton("2", callback_data='close_block_2')],
                [InlineKeyboardButton("3", callback_data='close_block_3')],
                [InlineKeyboardButton("4", callback_data='close_block_4')],
                [InlineKeyboardButton("5", callback_data='close_block_5')]
            ])
            await update.message.reply_text("Оцените блок ответов от 1 до 5:", reply_markup=reply_markup)
            context.user_data['awaiting_answer_block'] = True
        else:
            # Для открытых вопросов сразу переходим к следующему вопросу
            try:
                await save_evaluation_to_db(update, context)
                context.user_data['current_question'] += 1  # Переходим к следующему вопросу
                await send_next_question(update, context)  # Отправляем следующий вопрос
            except Exception as e:
                await update.message.reply_text(f"Ошибка при сохранении данных: {str(e)}")


# Функция для обработки оценки блока ответов
async def handle_answer_block_evaluation(update, context):
    """Обрабатываем оценку блока ответов и запрашиваем комментарий к блоку"""
    if context.user_data.get('awaiting_answer_block', False):
        # Получаем оценку от пользователя (извлекаем только числовую часть)
        rating = int(update.callback_query.data.split("_")[2])

        # Сохраняем оценку блока ответов
        current_question_index = context.user_data.get('current_question', 0)
        context.user_data['evaluations'][-1]['answer_block_rating'] = rating

        # Переходим к запросу комментария к блоку ответов
        await update.callback_query.message.reply_text("Пожалуйста, введите комментарий к блоку ответов:")
        context.user_data['awaiting_answer_block_comment'] = True
        # Логируем установку флага
        print("Флаг awaiting_answer_block_comment установлен в True.")
    else:
        print("Флаг awaiting_answer_block не установлен, функция не выполнена.")

# Функция для обработки комментария к блоку ответов
async def handle_answer_block_comment(update, context):
    """Обрабатываем комментарий к блоку ответов и сохраняем все данные по закрытому вопросу"""
    if context.user_data.get('awaiting_answer_block_comment', False):
        # Получаем комментарий от пользователя
        comment = update.message.text

        # Сохраняем комментарий для блока ответов
        current_question_index = context.user_data.get('current_question', 0)
        context.user_data['evaluations'][-1]['answer_block_comment'] = comment

        # Попробуем сохранить оценку и комментарий в базу данных
        try:
            # Сохраняем данные в базу
            await save_evaluation_to_db(update, context)

            # Переходим к следующему вопросу
            context.user_data['current_question'] += 1

            # Сбрасываем флаги
            context.user_data['awaiting_answer_block'] = False
            context.user_data['awaiting_answer_block_comment'] = False

            # Проверяем, остались ли еще вопросы, если да, отправляем следующий
            await send_next_question(update, context)  # Отправляем следующий вопрос
        except Exception as e:
            await update.message.reply_text(f"Ошибка при сохранении данных: {str(e)}")

async def save_evaluation_to_db(update, context):
    """Сохраняем текущий вопрос, оценки и комментарии в базу данных"""
    try:
        evaluation = context.user_data['evaluations'][-1]
        question_data = context.user_data['questions'][context.user_data['current_question']]

        # Проверка типа вопроса: открытый или закрытый
        print(context.user_data['is_open'])
        if context.user_data['is_open'] == "close":
            # Обработка закрытого вопроса (с вариантами ответов)
            print("Обработка закрытого вопроса")
            question_text = question_data['text']
            options = question_data['options']
            correct_answer = question_data['correct']
            question_rating = evaluation['rating']
            question_comment = evaluation.get('comment', "")
            answer_block_rating = evaluation.get('answer_block_rating', None)
            answer_block_comment = evaluation.get('answer_block_comment', "")

            question_type_id = 2  # Закрытые вопросы
            technology_id = context.user_data['technology']
            difficulty_id = context.user_data['level']

            # Создаем подключение к базе данных
            conn = create_connection("project_database.db")
            if conn is not None:
                # Сохраняем закрытый вопрос
                question_id = add_question(conn, question_text, question_type_id, technology_id, difficulty_id)

                # Сохраняем варианты ответов
                for i, option in enumerate(options):
                    is_correct = (chr(97 + i) == correct_answer)  # 'a' -> 97 в ASCII
                    add_answer(conn, question_id, option, is_correct)

                # Сохраняем оценку и комментарий к вопросу
                add_assessment(conn, update.effective_user.id, question_id, question_rating, question_comment)

                # Сохраняем оценку и комментарий к блоку ответов
                if answer_block_rating:
                    add_answer_assessment(conn, update.effective_user.id, question_id, answer_block_rating, answer_block_comment)

                # Закрываем соединение с базой данных
                conn.close()
            else:
                raise Exception("Не удалось подключиться к базе данных")

        else:
            # Обработка открытого вопроса (без вариантов ответов)
            question_text = question_data  # В открытых вопросах `question_data` — это строка с текстом вопроса
            question_rating = evaluation['rating']
            question_comment = evaluation.get('comment', "")

            question_type_id = 1  # Открытые вопросы
            technology_id = context.user_data['technology']
            difficulty_id = context.user_data['level']

            # Создаем подключение к базе данных
            conn = create_connection("project_database.db")
            if conn is not None:
                # Сохраняем открытый вопрос
                question_id = add_question(conn, question_text, question_type_id, technology_id, difficulty_id)

                # Сохраняем оценку и комментарий к вопросу
                add_assessment(conn, update.effective_user.id, question_id, question_rating, question_comment)

                # Закрываем соединение с базой данных
                conn.close()
            else:
                raise Exception("Не удалось подключиться к базе данных")

    except Exception as e:
        raise Exception(f"Не удалось сохранить данные: {str(e)}")
