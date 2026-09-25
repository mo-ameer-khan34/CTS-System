import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'trace-dev-secret-2025')

    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'trace_db')

    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'TRACE System <noreply@trace.gov.za>')

    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    FORCE_SAVE_PIN = os.getenv('FORCE_SAVE_PIN', 'TRACE9247')

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload

    ALLOWED_DOC_EXTENSIONS = {'pdf'}
    ALLOWED_EVIDENCE_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov', 'mkv', 'mp3', 'wav'}
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}

    OTP_EXPIRY_MINUTES = 30

    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Admin@TRACE2025')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@trace.gov.za')
