import sqlite3
import threading
import json

DB_NAME = "quiz_app.db"
lock = threading.Lock()

def init_db():
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            qr_code TEXT UNIQUE
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_by TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            question_text TEXT,
            answers_json TEXT,
            correct_answer INTEGER,
            FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            quiz_id INTEGER,
            question_id INTEGER,
            selected_answer INTEGER,
            is_correct BOOLEAN,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(student_id),
            FOREIGN KEY(quiz_id) REFERENCES quizzes(quiz_id),
            FOREIGN KEY(question_id) REFERENCES questions(question_id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS student_states (
            student_id INTEGER PRIMARY KEY,
            can_answer BOOLEAN DEFAULT 1,
            quiz_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )''')
        conn.commit()

def add_student(name, qr_code):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO students (name, qr_code) VALUES (?, ?)", (name, qr_code))
            conn.commit()
            print(f"Student '{name}' added successfully.")
            return c.lastrowid
        except sqlite3.IntegrityError:
            print(f"Student with QR code '{qr_code}' already exists.")
            c.execute("SELECT student_id FROM students WHERE qr_code = ?", (qr_code,))
            return c.fetchone()[0]

def remove_student(student_id):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        c.execute("DELETE FROM student_states WHERE student_id = ?", (student_id,))
        c.execute("DELETE FROM results WHERE student_id = ?", (student_id,))
        conn.commit()
        print(f"Student with ID '{student_id}' and associated data removed successfully.")

def get_student_by_qr_code(qr_code):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT student_id, name FROM students WHERE qr_code = ?", (qr_code,))
        student = c.fetchone()
        if student:
            return {'student_id': student[0], 'name': student[1]}
        return None

def get_all_students():
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT student_id, name FROM students")
        return [{'student_id': row[0], 'name': row[1]} for row in c.fetchall()]

def add_quiz(title, created_by, questions):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO quizzes (title, created_by) VALUES (?, ?)", (title, created_by))
        quiz_id = c.lastrowid
        for q in questions:
            answers_json = json.dumps(q['answers'])
            c.execute("INSERT INTO questions (quiz_id, question_text, answers_json, correct_answer) VALUES (?, ?, ?, ?)",
                      (quiz_id, q['question_text'], answers_json, q['correct']))
        conn.commit()
        return quiz_id

def get_latest_quiz():
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT quiz_id, title, created_by FROM quizzes ORDER BY quiz_id DESC LIMIT 1")
        quiz = c.fetchone()
        if quiz:
            return {'quiz_id': quiz[0], 'title': quiz[1], 'created_by': quiz[2]}
        return None

def get_questions_for_quiz(quiz_id):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT question_id, question_text, answers_json, correct_answer FROM questions WHERE quiz_id = ?", (quiz_id,))
        questions = []
        for row in c.fetchall():
            answers = json.loads(row[2])
            questions.append({
                'question_id': row[0],
                'question_text': row[1],
                'answers': answers,
                'correct_answer': row[3]
            })
        return questions

def get_question_by_id(question_id):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT question_id, question_text, answers_json, correct_answer FROM questions WHERE question_id = ?", (question_id,))
        question = c.fetchone()
        if question:
            answers = json.loads(question[2])
            return {
                'question_id': question[0],
                'question_text': question[1],
                'answers': answers,
                'correct_answer': question[3]
            }
        return None

def add_quiz_result(student_id, quiz_id, question_id, selected_answer, is_correct):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO results(student_id, quiz_id, question_id, selected_answer, is_correct) VALUES (?, ?, ?, ?, ?)''',
                  (student_id, quiz_id, question_id, selected_answer, is_correct))
        conn.commit()

def set_student_state(student_id, can_answer=None, quiz_active=None):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT student_id FROM student_states WHERE student_id = ?", (student_id,))
        exists = c.fetchone()
        if exists:
            update_parts = []
            params = []
            if can_answer is not None:
                update_parts.append("can_answer=?")
                params.append(can_answer)
            if quiz_active is not None:
                update_parts.append("quiz_active=?")
                params.append(quiz_active)
            if update_parts:
                params.append(student_id)
                c.execute(f"UPDATE student_states SET {', '.join(update_parts)} WHERE student_id=?", tuple(params))
        else:
            c.execute("INSERT INTO student_states (student_id, can_answer, quiz_active) VALUES (?, ?, ?)",
                      (student_id, can_answer if can_answer is not None else 1, quiz_active if quiz_active is not None else 1))
        conn.commit()

def get_student_state(student_id):
    with lock, sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT can_answer, quiz_active FROM student_states WHERE student_id = ?", (student_id,))
        state = c.fetchone()
        if state:
            return {'can_answer': bool(state[0]), 'quiz_active': bool(state[1])}
        return {'can_answer': True, 'quiz_active': True}

def get_quiz_results_by_teacher(teacher_name):
    with lock, sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT quiz_id, title FROM quizzes WHERE created_by = ?
        ''', (teacher_name,))
        quizzes = c.fetchall()

        results_data = []
        for quiz_row in quizzes:
            quiz_info = {
                'quiz_id': quiz_row['quiz_id'],
                'title': quiz_row['title'],
                'questions': []
            }

            c.execute('''
                SELECT question_id, question_text, answers_json, correct_answer
                FROM questions
                WHERE quiz_id = ?
                ORDER BY question_id ASC
            ''', (quiz_row['quiz_id'],))
            questions = c.fetchall()

            for question_row in questions:
                question_info = {
                    'question_id': question_row['question_id'],
                    'question_text': question_row['question_text'],
                    'answers': json.loads(question_row['answers_json']),
                    'correct_answer': question_row['correct_answer'],
                    'student_answers': []
                }

                c.execute('''
                    SELECT student_id, selected_answer, is_correct, timestamp
                    FROM results
                    WHERE quiz_id = ? AND question_id = ?
                    ORDER BY timestamp DESC
                ''', (quiz_row['quiz_id'], question_row['question_id']))
                student_results = c.fetchall()

                for res in student_results:
                    c.execute("SELECT name FROM students WHERE student_id = ?", (res['student_id'],))
                    student_name = c.fetchone()
                    student_name = student_name[0] if student_name else "Unknown Student"

                    question_info['student_answers'].append({
                        'student_id': res['student_id'],
                        'student_name': student_name,
                        'selected_answer': res['selected_answer'],
                        'is_correct': bool(res['is_correct']),
                        'timestamp': res['timestamp']
                    })
                quiz_info['questions'].append(question_info)
            results_data.append(quiz_info)
    return results_data

def get_quiz_results_by_student(student_id):
    with lock, sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
        student_name_row = c.fetchone()
        if not student_name_row:
            return None

        student_name = student_name_row['name']

        c.execute('''
            SELECT DISTINCT q.quiz_id, q.title, q.created_by
            FROM quizzes q
            JOIN results r ON q.quiz_id = r.quiz_id
            WHERE r.student_id = ?
            ORDER BY q.quiz_id ASC
        ''', (student_id,))
        quizzes = c.fetchall()

        results_data = []
        for quiz_row in quizzes:
            quiz_info = {
                'quiz_id': quiz_row['quiz_id'],
                'title': quiz_row['title'],
                'created_by': quiz_row['created_by'],
                'student_name': student_name,
                'questions': []
            }

            c.execute('''
                SELECT DISTINCT ques.question_id, ques.question_text, ques.answers_json, ques.correct_answer
                FROM questions ques
                JOIN results res ON ques.question_id = res.question_id
                WHERE res.quiz_id = ? AND res.student_id = ?
                ORDER BY ques.question_id ASC
            ''', (quiz_row['quiz_id'], student_id))
            questions = c.fetchall()

            for question_row in questions:
                question_info = {
                    'question_id': question_row['question_id'],
                    'question_text': question_row['question_text'],
                    'answers': json.loads(question_row['answers_json']),
                    'correct_answer': question_row['correct_answer'],
                    'student_answer': None
                }

                c.execute('''
                    SELECT selected_answer, is_correct, timestamp
                    FROM results
                    WHERE student_id = ? AND quiz_id = ? AND question_id = ?
                    ORDER BY timestamp DESC LIMIT 1
                ''', (student_id, quiz_row['quiz_id'], question_row['question_id']))
                student_result = c.fetchone()

                if student_result:
                    question_info['student_answer'] = {
                        'selected_answer': student_result['selected_answer'],
                        'is_correct': bool(student_result['is_correct']),
                        'timestamp': student_result['timestamp']
                    }
                quiz_info['questions'].append(question_info)
            results_data.append(quiz_info)
    return results_data