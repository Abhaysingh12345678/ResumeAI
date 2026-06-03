from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
from models.database import init_db, get_db
from utils.nlp_processor import extract_text_from_resume, extract_skills, match_resume_to_job, score_candidate
from utils.file_handler import allowed_file, save_resume

app = Flask(__name__)
app.secret_key = 'resumeai_secret_key_2024'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value) if value else []
    except Exception:
        return []

@app.template_global('enumerate')
def jinja_enumerate(iterable, start=0):
    return enumerate(iterable, start)

@app.template_filter('enumerate')
def jinja_enumerate_filter(iterable, start=0):
    return enumerate(iterable, start)

# Initialize DB on startup
with app.app_context():
    init_db()


# ─── Auth Routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Email already registered.', 'error')
            return render_template('register.html')

        hashed = generate_password_hash(password)
        db.execute(
            'INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, email, hashed, role, datetime.now().isoformat())
        )
        db.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ─── User Routes ─────────────────────────────────────────────────────────────

@app.route('/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    resumes = db.execute(
        'SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC',
        (session['user_id'],)
    ).fetchall()
    jobs = db.execute('SELECT * FROM job_descriptions ORDER BY created_at DESC').fetchall()
    matches = db.execute(
        '''SELECT mr.*, jd.title as job_title FROM match_results mr
           JOIN job_descriptions jd ON mr.job_id = jd.id
           WHERE mr.user_id = ? ORDER BY mr.match_score DESC''',
        (session['user_id'],)
    ).fetchall()

    return render_template('user_dashboard.html',
                           user=user, resumes=resumes, jobs=jobs, matches=matches)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        bio = request.form.get('bio', '').strip()
        db.execute(
            'UPDATE users SET name=?, phone=?, bio=? WHERE id=?',
            (name, phone, bio, session['user_id'])
        )
        db.commit()
        session['user_name'] = name
        flash('Profile updated.', 'success')

    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('profile.html', user=user)


@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'resume' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('user_dashboard'))

    file = request.files['resume']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('user_dashboard'))

    if not allowed_file(file.filename):
        flash('Only PDF, DOC, DOCX files are allowed.', 'error')
        return redirect(url_for('user_dashboard'))

    filename, filepath = save_resume(file, app.config['UPLOAD_FOLDER'], session['user_id'])
    extracted_text = extract_text_from_resume(filepath)
    skills = extract_skills(extracted_text)
    skills_json = json.dumps(skills)

    db = get_db()
    db.execute(
        'INSERT INTO resumes (user_id, filename, filepath, extracted_text, skills, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)',
        (session['user_id'], filename, filepath, extracted_text, skills_json, datetime.now().isoformat())
    )
    db.commit()
    flash('Resume uploaded and analyzed successfully!', 'success')
    return redirect(url_for('user_dashboard'))


@app.route('/match_resume/<int:resume_id>/<int:job_id>')
def match_resume(resume_id, job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    resume = db.execute('SELECT * FROM resumes WHERE id = ? AND user_id = ?',
                        (resume_id, session['user_id'])).fetchone()
    job = db.execute('SELECT * FROM job_descriptions WHERE id = ?', (job_id,)).fetchone()

    if not resume or not job:
        flash('Resume or Job not found.', 'error')
        return redirect(url_for('user_dashboard'))

    score, details = match_resume_to_job(resume['extracted_text'], job['description'],
                                         json.loads(resume['skills'] or '[]'),
                                         json.loads(job['required_skills'] or '[]'))

    existing = db.execute(
        'SELECT id FROM match_results WHERE user_id=? AND resume_id=? AND job_id=?',
        (session['user_id'], resume_id, job_id)
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE match_results SET match_score=?, details=?, matched_at=? WHERE id=?',
            (score, json.dumps(details), datetime.now().isoformat(), existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO match_results (user_id, resume_id, job_id, match_score, details, matched_at) VALUES (?,?,?,?,?,?)',
            (session['user_id'], resume_id, job_id, score, json.dumps(details), datetime.now().isoformat())
        )
    db.commit()

    flash(f'Match score: {score:.1f}%', 'success')
    return redirect(url_for('view_match_results'))


@app.route('/match_results')
def view_match_results():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    matches = db.execute(
        '''SELECT mr.*, jd.title as job_title, jd.company, r.filename as resume_name
           FROM match_results mr
           JOIN job_descriptions jd ON mr.job_id = jd.id
           JOIN resumes r ON mr.resume_id = r.id
           WHERE mr.user_id = ?
           ORDER BY mr.match_score DESC''',
        (session['user_id'],)
    ).fetchall()

    return render_template('match_results.html', matches=matches)


@app.route('/job_descriptions')
def job_descriptions():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    jobs = db.execute('SELECT * FROM job_descriptions ORDER BY created_at DESC').fetchall()
    resumes = db.execute('SELECT * FROM resumes WHERE user_id = ?', (session['user_id'],)).fetchall()
    return render_template('job_descriptions.html', jobs=jobs, resumes=resumes)


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = get_db()
    total_users = db.execute("SELECT COUNT(*) as c FROM users WHERE role='user'").fetchone()['c']
    total_resumes = db.execute("SELECT COUNT(*) as c FROM resumes").fetchone()['c']
    total_jobs = db.execute("SELECT COUNT(*) as c FROM job_descriptions").fetchone()['c']
    total_matches = db.execute("SELECT COUNT(*) as c FROM match_results").fetchone()['c']

    recent_users = db.execute(
        "SELECT * FROM users WHERE role='user' ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    top_candidates = db.execute(
        '''SELECT u.name, u.email, AVG(mr.match_score) as avg_score, COUNT(mr.id) as match_count
           FROM match_results mr JOIN users u ON mr.user_id = u.id
           GROUP BY mr.user_id ORDER BY avg_score DESC LIMIT 5'''
    ).fetchall()

    return render_template('admin_dashboard.html',
                           total_users=total_users, total_resumes=total_resumes,
                           total_jobs=total_jobs, total_matches=total_matches,
                           recent_users=recent_users, top_candidates=top_candidates)


@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = get_db()
    users = db.execute("SELECT u.*, COUNT(r.id) as resume_count FROM users u LEFT JOIN resumes r ON u.id = r.user_id WHERE u.role='user' GROUP BY u.id ORDER BY u.created_at DESC").fetchall()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM match_results WHERE user_id=?', (user_id,))
    db.execute('DELETE FROM resumes WHERE user_id=?', (user_id,))
    db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/jobs', methods=['GET', 'POST'])
def admin_jobs():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company = request.form.get('company', '').strip()
        description = request.form.get('description', '').strip()
        required_skills_raw = request.form.get('required_skills', '')
        skills_list = [s.strip() for s in required_skills_raw.split(',') if s.strip()]

        db.execute(
            'INSERT INTO job_descriptions (title, company, description, required_skills, created_at) VALUES (?,?,?,?,?)',
            (title, company, description, json.dumps(skills_list), datetime.now().isoformat())
        )
        db.commit()
        flash('Job description added.', 'success')

    jobs = db.execute('SELECT * FROM job_descriptions ORDER BY created_at DESC').fetchall()
    return render_template('admin_jobs.html', jobs=jobs)


@app.route('/admin/jobs/delete/<int:job_id>', methods=['POST'])
def admin_delete_job(job_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM match_results WHERE job_id=?', (job_id,))
    db.execute('DELETE FROM job_descriptions WHERE id=?', (job_id,))
    db.commit()
    flash('Job deleted.', 'success')
    return redirect(url_for('admin_jobs'))


@app.route('/admin/scores')
def admin_scores():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = get_db()
    scores = db.execute(
        '''SELECT mr.*, u.name as candidate_name, u.email,
                  jd.title as job_title, jd.company, r.filename as resume_file
           FROM match_results mr
           JOIN users u ON mr.user_id = u.id
           JOIN job_descriptions jd ON mr.job_id = jd.id
           JOIN resumes r ON mr.resume_id = r.id
           ORDER BY mr.match_score DESC'''
    ).fetchall()
    return render_template('admin_scores.html', scores=scores)


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.route('/api/resume/<int:resume_id>')
def api_resume(resume_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    resume = db.execute('SELECT * FROM resumes WHERE id=? AND user_id=?',
                        (resume_id, session['user_id'])).fetchone()
    if not resume:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': resume['id'],
        'filename': resume['filename'],
        'skills': json.loads(resume['skills'] or '[]'),
        'uploaded_at': resume['uploaded_at']
    })


@app.route('/api/stats')
def api_stats():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    monthly = db.execute(
        "SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count FROM users WHERE role='user' GROUP BY month ORDER BY month DESC LIMIT 6"
    ).fetchall()
    return jsonify({'monthly_registrations': [dict(r) for r in monthly]})


if __name__ == '__main__':
    app.run( debug=True, port=5000)
