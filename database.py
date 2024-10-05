import sqlite3
from sqlite3 import Error

# Функция для создания подключения к базе данных SQLite
def create_connection(db_file):
    """Создаем подключение к базе данных SQLite"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn

# Функция для создания таблиц в базе данных
def create_tables(conn):
    """Создаем таблицы"""
    try:
        cursor = conn.cursor()

        # SQL для создания таблицы пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE
            );
        ''')

        # SQL для создания таблицы вопросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                question_type_id INTEGER NOT NULL,
                technology_id INTEGER NOT NULL,
                difficulty_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_type_id) REFERENCES question_types(id),
                FOREIGN KEY (technology_id) REFERENCES technologies(id),
                FOREIGN KEY (difficulty_id) REFERENCES difficulty(id)
            );
        ''')

        # SQL для создания таблицы типов вопросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_name TEXT UNIQUE NOT NULL
            );
        ''')

        # SQL для создания таблицы технологий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS technologies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tech_name TEXT UNIQUE NOT NULL
            );
        ''')

        # SQL для создания таблицы уровней сложности
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS difficulty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level_name TEXT UNIQUE NOT NULL
            );
        ''')

        # SQL для создания таблицы ответов на закрытые вопросы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                answer_text TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );
        ''')

        # SQL для создания таблицы оценок вариантов ответов на закрытые вопросы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS answers_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                assessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );
        ''')

        # SQL для создания таблицы оценок вопросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                assessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );
        ''')

        conn.commit()
    except Error as e:
        print(f"Ошибка при создании таблиц: {e}")

# Функция для заполнения таблиц technologies, difficulty и question_types
def fill_base_tables(conn):
    """Заполняем таблицы базовыми данными из promts.py"""

    try:
        cursor = conn.cursor()

        # Заполнение таблицы technologies
        technologies = ["Python", "C++", "C#", "Java", "Java Script", "1C", "Goland"]  # данные из promts.py
        for tech in technologies:
            cursor.execute('''INSERT OR IGNORE INTO technologies (tech_name) VALUES (?)''', (tech,))

        # Заполнение таблицы difficulty
        difficulty_levels = ["junior", "junior+", "middle", "middle+", "senior"]  # данные из promts.py
        for level in difficulty_levels:
            cursor.execute('''INSERT OR IGNORE INTO difficulty (level_name) VALUES (?)''', (level,))

        # Заполнение таблицы question_types
        question_types = ["open", "close"]  # данные из promts.py
        for q_type in question_types:
            cursor.execute('''INSERT OR IGNORE INTO question_types (type_name) VALUES (?)''', (q_type,))

        conn.commit()

    except Error as e:
        print(f"Ошибка при заполнении таблиц: {e}")

# Функция для добавления нового пользователя
def add_user(conn, telegram_id, name, email):
    """Добавление нового пользователя в базу данных или обновление существующего"""
    try:
        cursor = conn.cursor()

        # Проверяем, существует ли пользователь с таким telegram_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()

        if result:
            # Пользователь уже существует, можно обновить данные, если нужно
            print(f"Пользователь с telegram_id {telegram_id} уже существует. Обновление информации.")
            sql = '''UPDATE users SET name = ?, email = ? WHERE telegram_id = ?'''
            cursor.execute(sql, (name, email, telegram_id))
        else:
            # Добавляем нового пользователя
            sql = '''INSERT INTO users(telegram_id, name, email)
                     VALUES(?, ?, ?)'''
            cursor.execute(sql, (telegram_id, name, email))

        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"Ошибка при добавлении или обновлении пользователя: {e}")

# Функция для добавления нового вопроса
def add_question(conn, question_text, question_type_id, technology_id, difficulty_id):
    """Добавление нового вопроса в базу данных"""
    try:
        sql = '''INSERT INTO questions(question_text, question_type_id, technology_id, difficulty_id)
                 VALUES(?, ?, ?, ?)'''
        cursor = conn.cursor()
        cursor.execute(sql, (question_text, question_type_id, technology_id, difficulty_id))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"Ошибка при добавлении вопроса: {e}")

# Функция для добавления нового ответа на закрытый вопрос
def add_answer(conn, question_id, answer_text, is_correct):
    """Добавление нового ответа в базу данных"""
    try:
        sql = '''INSERT INTO answers(question_id, answer_text, is_correct)
                 VALUES(?, ?, ?)'''
        cursor = conn.cursor()
        cursor.execute(sql, (question_id, answer_text, is_correct))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"Ошибка при добавлении ответа: {e}")

# Функция для добавления оценки ответа
def add_answer_assessment(conn, user_id, question_id, rating, comment):
    """Добавление оценки вариантов ответа для закрытого вопроса"""
    try:
        sql = '''INSERT INTO answers_assessments(user_id, question_id, rating, comment)
                 VALUES(?, ?, ?, ?)'''
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, question_id, rating, comment))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"Ошибка при добавлении оценки ответа: {e}")

# Функция для добавления оценки вопроса
def add_assessment(conn, user_id, question_id, rating, comment):
    """Добавление оценки вопроса"""
    try:
        sql = '''INSERT INTO assessments(user_id, question_id, rating, comment)
                 VALUES(?, ?, ?, ?)'''
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, question_id, rating, comment))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"Ошибка при добавлении оценки вопроса: {e}")
