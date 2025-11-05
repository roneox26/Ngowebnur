import os


SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key_here')

# Use /tmp for serverless environments like Vercel
if os.environ.get('VERCEL'):
    db_path = os.path.join(tempfile.gettempdir(), 'loan.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
else:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///loan.db')

if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
