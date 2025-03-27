import os

# Base configuration class
class Config:
    # Flask
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # Database
    database_url = os.environ.get('DATABASE_URL')
    # Fix for PostgreSQL URLs that start with 'postgres://'
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///legal_analyzer.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'rtf'}
    
    # Legal API settings
    LEGAL_API_KEY = os.environ.get('LEGAL_API_KEY', '')
    LEGAL_API_BASE_URL = os.environ.get('LEGAL_API_BASE_URL', 'https://api.law.gov/v1')
    
    # NLP Models
    NLP_MODEL_PATH = os.environ.get('NLP_MODEL_PATH', 'en_core_web_lg')
    
    # API Authentication
    API_TOKEN_EXPIRATION = 3600  # 1 hour in seconds


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Get the correct configuration based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    config_name = os.environ.get('FLASK_ENV', 'default')
    return config.get(config_name, config['default'])
