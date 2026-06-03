import sqlite3
import os
from flask import g

DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resumeai.db')


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',
            phone       TEXT,
            bio         TEXT,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS resumes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(id),
            filename       TEXT    NOT NULL,
            filepath       TEXT    NOT NULL,
            extracted_text TEXT,
            skills         TEXT,
            uploaded_at    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS job_descriptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            company         TEXT,
            description     TEXT NOT NULL,
            required_skills TEXT,
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS match_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            resume_id   INTEGER NOT NULL REFERENCES resumes(id),
            job_id      INTEGER NOT NULL REFERENCES job_descriptions(id),
            match_score REAL    NOT NULL DEFAULT 0,
            details     TEXT,
            matched_at  TEXT    NOT NULL
        );
    ''')

    # Seed admin account
    from werkzeug.security import generate_password_hash
    from datetime import datetime
    existing = db.execute("SELECT id FROM users WHERE email='admin@resumeai.com'").fetchone()
    if not existing:
        db.execute(
            "INSERT INTO users (name, email, password, role, created_at) VALUES (?,?,?,?,?)",
            ('Admin', 'admin@resumeai.com', generate_password_hash('admin123'), 'admin', datetime.now().isoformat())
        )

    # Seed sample jobs
    job_count = db.execute("SELECT COUNT(*) as c FROM job_descriptions").fetchone()['c']
    if job_count == 0:
        import json
        sample_jobs = [
            ('Python Backend Developer', 'TechCorp India',
             'We need a skilled Python developer with Flask/Django experience, REST API design, and database management. Experience with cloud deployment is a plus.',
             json.dumps(['Python', 'Flask', 'Django', 'REST API', 'SQL', 'PostgreSQL', 'Git', 'Docker'])),
            ('Data Scientist', 'Analytics Pro',
             'Looking for a Data Scientist with experience in machine learning, NLP, and data visualization. Strong Python and statistics background required.',
             json.dumps(['Python', 'Machine Learning', 'NLP', 'scikit-learn', 'Pandas', 'NumPy', 'TensorFlow', 'SQL'])),
            ('Full Stack Developer', 'StartupXYZ',
             'Full Stack Developer needed with React/Vue frontend skills and Node.js or Python backend. Experience with MongoDB and REST APIs required.',
             json.dumps(['JavaScript', 'React', 'HTML', 'CSS', 'Node.js', 'Python', 'MongoDB', 'REST API'])),
            ('DevOps Engineer', 'CloudBase',
             'DevOps engineer with strong Linux, Docker, Kubernetes, and CI/CD pipeline experience. AWS/GCP certification preferred.',
             json.dumps(['Docker', 'Kubernetes', 'Linux', 'CI/CD', 'AWS', 'Git', 'Bash', 'Terraform'])),
            ('Machine Learning Engineer', 'AI Ventures',
             'ML Engineer to design and deploy production ML models. Strong Python, deep learning, and MLOps experience required.',
             json.dumps(['Python', 'TensorFlow', 'PyTorch', 'scikit-learn', 'MLOps', 'Docker', 'SQL', 'NLP'])),
        ]
        now = datetime.now().isoformat()
        for title, company, desc, skills in sample_jobs:
            db.execute(
                'INSERT INTO job_descriptions (title, company, description, required_skills, created_at) VALUES (?,?,?,?,?)',
                (title, company, desc, skills, now)
            )

    db.commit()
    db.close()
