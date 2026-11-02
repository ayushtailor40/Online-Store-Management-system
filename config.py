import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration settings."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'smart-online-store-secret-key-2026')
    
    # Database Settings
    # DB_TYPE can be 'mysql' (default) or 'sqlite'
    DB_TYPE = os.getenv('DB_TYPE', 'mysql').lower()
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'online_store_db')
    
    # SQLite fallback file path (used if DB_TYPE=sqlite or MySQL unavailable in local dev/testing)
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'online_store.db')
    
    # Pagination & Display Defaults
    ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', 10))
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds

class TestingConfig(Config):
    """Configuration for automated tests."""
    TESTING = True
    DB_TYPE = 'sqlite'
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'tests', 'test_online_store.db')
    WTF_CSRF_ENABLED = False
