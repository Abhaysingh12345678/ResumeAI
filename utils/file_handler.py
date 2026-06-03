import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_resume(file, upload_folder: str, user_id: int) -> tuple:
    """Save an uploaded resume file and return (filename, filepath)."""
    original = secure_filename(file.filename)
    ext = original.rsplit('.', 1)[-1].lower()
    unique_name = f"user{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(upload_folder, unique_name)
    file.save(filepath)
    return unique_name, filepath
