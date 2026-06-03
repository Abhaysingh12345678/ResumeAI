# ResumeAI — Intelligent Resume Screening System

A full-stack web application built with **Python Flask**, **NLP**, **HTML/CSS/JS**, and **SQLite** for automated resume screening, skill extraction, and candidate matching.

---

## 🚀 Features

| Module | Description |
|--------|-------------|
| **User Module** | Registration, Login, Dashboard, Upload Resume, View Jobs, View Match Results, Profile |
| **Admin Module** | Login, Manage Users, Manage Job Descriptions, View Candidate Scores |
| **AI/ML Module** | Resume Text Extraction, Skill Extraction using NLP, Resume–Job Matching (TF-IDF + Cosine Similarity), Candidate Scoring & Ranking |
| **Authentication** | Role-Based Access Control (User / Admin), Password Hashing |
| **Database Module** | SQLite — Users, Resumes, Job Descriptions, Match Results |
| **API Module** | RESTful JSON endpoints for resumes and stats |
| **Frontend** | Responsive dark-theme UI, animated score rings, progress bars |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask 3.x
- **Frontend**: HTML5, CSS3 (custom dark theme), Vanilla JS
- **Database**: SQLite (via Python stdlib `sqlite3`)
- **NLP**: Custom TF-IDF + keyword matching (no external ML model required)
- **PDF Parsing**: pdfminer.six
- **DOCX Parsing**: python-docx

---

## ⚙️ Setup & Run

### 1. Clone / unzip the project
```bash
cd resumeai
```

### 2. Create virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
python app.py
```

### 5. Open in browser
```
http://127.0.0.1:5000
```

---

## 🔑 Default Credentials

| Role  | Email                  | Password   |
|-------|------------------------|------------|
| Admin | admin@resumeai.com     | admin123   |

Register as a **Candidate** to test the user flow.

---

## 📁 Project Structure

```
resumeai/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── resumeai.db             # SQLite database (auto-created)
├── models/
│   ├── __init__.py
│   └── database.py         # DB init, schema, seed data
├── utils/
│   ├── __init__.py
│   ├── nlp_processor.py    # NLP: extraction, matching, scoring
│   └── file_handler.py     # File upload utilities
├── static/
│   ├── css/style.css       # Main stylesheet (dark theme)
│   ├── js/main.js          # Frontend JavaScript
│   └── uploads/            # Uploaded resumes (gitignored)
└── templates/
    ├── base.html           # Base layout with navbar
    ├── index.html          # Landing page
    ├── login.html          # Login form
    ├── register.html       # Registration form
    ├── user_dashboard.html # Candidate dashboard
    ├── job_descriptions.html
    ├── match_results.html
    ├── profile.html
    ├── admin_dashboard.html
    ├── admin_users.html
    ├── admin_jobs.html
    └── admin_scores.html
```

---

## 🧠 NLP Algorithm

The matching score is computed from **three components**:

| Component         | Weight | Method |
|------------------|--------|--------|
| Skill Overlap     | 50%    | Intersection of extracted vs required skills |
| Content Similarity | 30%   | TF-IDF cosine similarity (pure Python stdlib) |
| Keyword Density   | 20%    | Fraction of job keywords found in resume |

**Final Score = 0.50 × skill + 0.30 × cosine + 0.20 × density**

---

## 📦 Deliverables (as per project spec)

- ✅ Source code (this repository)
- ✅ Project Report (see `/docs/report.md` or generate from this README)
- ✅ REST API endpoints (`/api/resume/<id>`, `/api/stats`)
- ✅ All 7 modules implemented
- ✅ Role-based access control

---

## 📧 Contact

Built for **CountryEdu Private Limited** internship project.
GSTIN: 06AAJCC6151A1Z3 | CIN: U72900HR2021PTC096283
