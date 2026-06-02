from functools import wraps
from flask import session, redirect, url_for, flash
import hashlib
from backend.database import get_db_connection

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('请先登录', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('无权访问此页面', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_login(username, password):
    conn = get_db_connection()
    hashed_pwd = hashlib.md5(password.encode()).hexdigest()
    user = conn.execute(
        "SELECT id, username, role, real_name FROM users WHERE username = ? AND password = ?",
        (username, hashed_pwd)
    ).fetchone()
    conn.close()
    return dict(user) if user else None