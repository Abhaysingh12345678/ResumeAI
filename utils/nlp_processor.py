"""
NLP Processor — resume text extraction, skill extraction, and matching.
Uses re / collections (stdlib) + optional pdfminer / python-docx for file parsing.
Falls back gracefully when optional libraries aren't installed.
"""
import re
import json
import math
from collections import Counter

# ─── Master skill vocabulary ────────────────────────────────────────────────

SKILL_KEYWORDS = [
    # Languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'rust',
    'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'bash', 'perl',
    # Web / Frontend
    'html', 'css', 'react', 'angular', 'vue', 'jquery', 'bootstrap', 'tailwind',
    'sass', 'webpack', 'next.js', 'nuxt',
    # Backend
    'flask', 'django', 'fastapi', 'express', 'spring', 'laravel', 'rails', 'node.js',
    'asp.net', 'rest api', 'graphql', 'websocket',
    # Databases
    'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis', 'elasticsearch',
    'cassandra', 'dynamodb', 'oracle', 'firebase',
    # ML / AI
    'machine learning', 'deep learning', 'nlp', 'computer vision', 'tensorflow',
    'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy', 'scipy', 'matplotlib',
    'seaborn', 'opencv', 'huggingface', 'transformers', 'spacy', 'nltk',
    # DevOps / Cloud
    'docker', 'kubernetes', 'aws', 'gcp', 'azure', 'ci/cd', 'jenkins', 'github actions',
    'terraform', 'ansible', 'linux', 'nginx', 'apache',
    # Tools
    'git', 'github', 'gitlab', 'jira', 'vs code', 'pycharm', 'intellij', 'postman',
    'figma', 'adobe xd',
    # Methodologies
    'agile', 'scrum', 'kanban', 'tdd', 'microservices', 'devops', 'mlops',
    # Soft / other
    'problem solving', 'communication', 'teamwork', 'leadership', 'project management',
]


# ─── Text extraction ─────────────────────────────────────────────────────────

def extract_text_from_resume(filepath: str) -> str:
    """Extract plain text from PDF, DOCX, or TXT resume files."""
    ext = filepath.rsplit('.', 1)[-1].lower()

    if ext == 'pdf':
        return _extract_pdf(filepath)
    elif ext in ('doc', 'docx'):
        return _extract_docx(filepath)
    elif ext == 'txt':
        try:
            with open(filepath, 'r', errors='ignore') as f:
                return f.read()
        except Exception:
            return ''
    return ''


def _extract_pdf(filepath: str) -> str:
    try:
        from pdfminer.high_level import extract_text
        return extract_text(filepath) or ''
    except ImportError:
        pass
    try:
        import PyPDF2
        text = []
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text() or '')
        return '\n'.join(text)
    except Exception:
        return '[PDF text extraction unavailable — install pdfminer.six]'


def _extract_docx(filepath: str) -> str:
    try:
        import docx
        doc = docx.Document(filepath)
        return '\n'.join(p.text for p in doc.paragraphs)
    except Exception:
        return '[DOCX text extraction unavailable — install python-docx]'


# ─── Skill extraction ────────────────────────────────────────────────────────

def extract_skills(text: str) -> list:
    """Return list of skills found in the resume text."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        # whole-word / phrase match
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill.title())
    return list(dict.fromkeys(found))  # preserve order, deduplicate


# ─── Resume → Job matching ───────────────────────────────────────────────────

def match_resume_to_job(resume_text: str, job_text: str,
                        resume_skills: list, job_skills: list) -> tuple:
    """
    Compute a match score (0-100) and breakdown details dict.
    Three weighted components:
      1. Skill overlap (50 %)
      2. TF-IDF cosine similarity on raw text (30 %)
      3. Keyword density bonus (20 %)
    """
    # 1. Skill overlap
    rs = {s.lower() for s in resume_skills}
    js = {s.lower() for s in job_skills}
    if js:
        skill_overlap = rs & js
        skill_score = (len(skill_overlap) / len(js)) * 100
    else:
        skill_overlap = set()
        skill_score = 50.0   # neutral if no required skills listed

    # 2. TF-IDF cosine similarity
    cosine_score = _tfidf_cosine(resume_text, job_text) * 100

    # 3. Keyword density bonus
    density_score = _keyword_density(resume_text, job_text) * 100

    # Weighted total
    total = skill_score * 0.50 + cosine_score * 0.30 + density_score * 0.20
    total = round(min(max(total, 0), 100), 2)

    missing_skills = list(js - rs)[:10]
    matched_skills = [s.title() for s in skill_overlap]

    details = {
        'skill_score': round(skill_score, 1),
        'cosine_score': round(cosine_score, 1),
        'density_score': round(density_score, 1),
        'matched_skills': matched_skills,
        'missing_skills': [s.title() for s in missing_skills],
        'total_required': len(js),
        'total_matched': len(skill_overlap),
    }
    return total, details


def score_candidate(resume_text: str, job_text: str) -> float:
    rs = extract_skills(resume_text)
    js = extract_skills(job_text)
    score, _ = match_resume_to_job(resume_text, job_text, rs, js)
    return score


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list:
    return re.findall(r'\b[a-z]{2,}\b', text.lower())


def _tfidf_cosine(text_a: str, text_b: str) -> float:
    """Simple TF-IDF cosine similarity between two documents."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0

    vocab = set(tokens_a) | set(tokens_b)
    tf_a = Counter(tokens_a)
    tf_b = Counter(tokens_b)

    # Build TF vectors (normalised)
    def tf_vec(tf, total):
        return {w: tf[w] / total for w in vocab}

    vec_a = tf_vec(tf_a, len(tokens_a))
    vec_b = tf_vec(tf_b, len(tokens_b))

    dot = sum(vec_a.get(w, 0) * vec_b.get(w, 0) for w in vocab)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return min(dot / (mag_a * mag_b), 1.0)


def _keyword_density(resume_text: str, job_text: str) -> float:
    """Fraction of job keywords that appear in the resume."""
    job_tokens = set(_tokenize(job_text))
    resume_tokens = set(_tokenize(resume_text))
    # Remove stopwords
    stopwords = {'the', 'and', 'for', 'with', 'are', 'you', 'our', 'will', 'have',
                 'this', 'that', 'from', 'your', 'we', 'an', 'is', 'in', 'of',
                 'to', 'a', 'be', 'as', 'or', 'at', 'by', 'it'}
    job_tokens -= stopwords
    if not job_tokens:
        return 0.5
    overlap = job_tokens & resume_tokens
    return len(overlap) / len(job_tokens)
