import sqlite3
import hashlib
import os

DB_PATH = 'instance/course_work.db'

def init_db():
    os.makedirs('instance', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            real_name TEXT NOT NULL,
            class_name TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            teacher_id INTEGER NOT NULL,
            deadline TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            content TEXT,
            submit_time TEXT NOT NULL,
            score INTEGER DEFAULT NULL,
            feedback TEXT,
            status TEXT DEFAULT 'submitted'
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_pwd = hashlib.md5('123456'.encode()).hexdigest()
        
        cursor.execute('INSERT INTO users (username, password, role, real_name) VALUES (?, ?, ?, ?)',
                       ('student1', default_pwd, 'student', '张三'))
        cursor.execute('INSERT INTO users (username, password, role, real_name) VALUES (?, ?, ?, ?)',
                       ('student2', default_pwd, 'student', '李四'))
        cursor.execute('INSERT INTO users (username, password, role, real_name) VALUES (?, ?, ?, ?)',
                       ('teacher1', default_pwd, 'teacher', '王老师'))
        cursor.execute('INSERT INTO users (username, password, role, real_name) VALUES (?, ?, ?, ?)',
                       ('admin1', default_pwd, 'admin', '超级管理员'))
        
        cursor.execute('INSERT INTO assignments (title, description, teacher_id, deadline, created_at) VALUES (?, ?, ?, ?, ?)',
                       ('第一次作业：Python基础', '请完成课后练习题1-10', 3, '2026-06-15 23:59:59', '2026-06-01 10:00:00'))
        cursor.execute('INSERT INTO assignments (title, description, teacher_id, deadline, created_at) VALUES (?, ?, ?, ?, ?)',
                       ('第二次作业：Web开发', '使用Flask搭建一个简单的博客系统', 3, '2026-06-22 23:59:59', '2026-06-08 10:00:00'))
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_db()