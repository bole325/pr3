from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import hashlib
from backend.database import init_db, get_db_connection
from backend.auth import login_required, check_login

app = Flask(__name__, template_folder='../frontend', static_folder='../frontend')
app.secret_key = 'your-secret-key'

init_db()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = check_login(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['real_name'] = user['real_name']
            flash(f'欢迎回来，{user["real_name"]}！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    role = session.get('role')
    if role == 'student':
        return redirect(url_for('student_dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/student')
@login_required(role='student')
def student_dashboard():
    conn = get_db_connection()
    assignments = conn.execute('''
        SELECT a.*, u.real_name as teacher_name,
               (SELECT status FROM submissions WHERE assignment_id = a.id AND student_id = ?) as submit_status,
               (SELECT score FROM submissions WHERE assignment_id = a.id AND student_id = ?) as score,
               (SELECT feedback FROM submissions WHERE assignment_id = a.id AND student_id = ?) as feedback
        FROM assignments a JOIN users u ON a.teacher_id = u.id
    ''', (session['user_id'], session['user_id'], session['user_id'])).fetchall()
    conn.close()
    return render_template('student.html', assignments=assignments)

@app.route('/submit_assignment/<int:assignment_id>', methods=['POST'])
@login_required(role='student')
def submit_assignment(assignment_id):
    content = request.form.get('content', '').strip()
    if not content:
        flash('请输入作业内容', 'danger')
        return redirect(url_for('student_dashboard'))
    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM submissions WHERE assignment_id = ? AND student_id = ?",
                           (assignment_id, session['user_id'])).fetchone()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if existing:
        conn.execute("UPDATE submissions SET content = ?, submit_time = ?, status = 'resubmitted' WHERE id = ?",
                    (content, now, existing['id']))
        flash('作业已更新', 'info')
    else:
        conn.execute("INSERT INTO submissions (assignment_id, student_id, content, submit_time, status) VALUES (?, ?, ?, ?, ?)",
                    (assignment_id, session['user_id'], content, now, 'submitted'))
        flash('作业提交成功', 'success')
    conn.commit()
    conn.close()
    return redirect(url_for('student_dashboard'))

@app.route('/my_submissions')
@login_required(role='student')
def my_submissions():
    conn = get_db_connection()
    submissions = conn.execute('''
        SELECT s.*, a.title as assignment_title, u.real_name as teacher_name
        FROM submissions s JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON a.teacher_id = u.id WHERE s.student_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_submissions.html', submissions=submissions)

@app.route('/teacher')
@login_required(role='teacher')
def teacher_dashboard():
    conn = get_db_connection()
    assignments = conn.execute('''
        SELECT a.*, (SELECT COUNT(*) FROM submissions WHERE assignment_id = a.id) as submit_count
        FROM assignments a WHERE a.teacher_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('teacher.html', assignments=assignments)

@app.route('/create_assignment', methods=['POST'])
@login_required(role='teacher')
def create_assignment():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    deadline = request.form.get('deadline')
    if not title:
        flash('作业标题不能为空', 'danger')
        return redirect(url_for('teacher_dashboard'))
    conn = get_db_connection()
    conn.execute("INSERT INTO assignments (title, description, teacher_id, deadline, created_at) VALUES (?, ?, ?, ?, ?)",
                (title, description, session['user_id'], deadline, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    flash('作业发布成功', 'success')
    return redirect(url_for('teacher_dashboard'))

@app.route('/grade_assignment/<int:assignment_id>')
@login_required(role='teacher')
def grade_assignment(assignment_id):
    conn = get_db_connection()
    assignment = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
    submissions = conn.execute('''
        SELECT s.*, u.real_name as student_name
        FROM submissions s JOIN users u ON s.student_id = u.id WHERE s.assignment_id = ?
    ''', (assignment_id,)).fetchall()
    conn.close()
    return render_template('grade.html', submissions=submissions, assignment=assignment)

@app.route('/save_score', methods=['POST'])
@login_required(role='teacher')
def save_score():
    submission_id = request.form.get('submission_id')
    score = request.form.get('score')
    feedback = request.form.get('feedback', '')
    conn = get_db_connection()
    conn.execute("UPDATE submissions SET score = ?, feedback = ?, status = 'graded' WHERE id = ?",
                (score, feedback, submission_id))
    conn.commit()
    conn.close()
    flash('成绩已保存', 'success')
    return redirect(request.referrer or url_for('teacher_dashboard'))

@app.route('/admin')
@login_required(role='admin')
def admin_dashboard():
    conn = get_db_connection()
    stats = {
        'student_count': conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        'teacher_count': conn.execute("SELECT COUNT(*) FROM users WHERE role='teacher'").fetchone()[0],
        'assignment_count': conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0],
        'submission_count': conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    }
    users = conn.execute("SELECT * FROM users ORDER BY role, id").fetchall()
    conn.close()
    return render_template('admin.html', stats=stats, users=users)

@app.route('/add_user', methods=['POST'])
@login_required(role='admin')
def add_user():
    username = request.form.get('username')
    real_name = request.form.get('real_name')
    role = request.form.get('role')
    default_pwd = hashlib.md5('123456'.encode()).hexdigest()
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password, role, real_name) VALUES (?, ?, ?, ?)",
                    (username, default_pwd, role, real_name))
        conn.commit()
        flash(f'用户 {username} 添加成功，默认密码：123456', 'success')
    except:
        flash('添加失败，用户名可能已存在', 'danger')
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<int:user_id>')
@login_required(role='admin')
def delete_user(user_id):
    if user_id == session['user_id']:
        flash('不能删除自己', 'danger')
        return redirect(url_for('admin_dashboard'))
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash('用户已删除', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/export_data')
@login_required(role='admin')
def export_data():
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, real_name, role FROM users").fetchall()
    assignments = conn.execute("SELECT * FROM assignments").fetchall()
    submissions = conn.execute("SELECT * FROM submissions").fetchall()
    data = {
        'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'users': [dict(row) for row in users],
        'assignments': [dict(row) for row in assignments],
        'submissions': [dict(row) for row in submissions]
    }
    conn.close()
    response = jsonify(data)
    response.headers['Content-Disposition'] = 'attachment; filename=export_data.json'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)