"""
Django test settings for RAG Chatbot SaaS.

Optimized configuration for fast, reliable testing with proper isolation.
"""

import sys
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Basic Django settings for testing
SECRET_KEY = 'test-secret-key-for-testing-only-not-for-production'
DEBUG = False
TESTING = True

ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Application definition - simplified for testing
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth", 
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.chatbots", 
    "apps.knowledge",
    "apps.conversations",
    "apps.billing",
    "apps.webhooks",
    "apps.core",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware", 
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "chatbot_saas.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request", 
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Auth configuration
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Override for testing
SECRET_KEY = 'test-secret-key-for-testing-only-not-for-production'
DEBUG = False
TESTING = True

# Fast password hashers for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use in-memory SQLite for fast tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST': {
            'NAME': ':memory:',
        },
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# Disable migrations for speed
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Fast caching for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Disable Celery for synchronous testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Add missing Celery settings required by celery.py
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_WORKER_CONCURRENCY = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 10
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 1000
CELERY_TASK_SOFT_TIME_LIMIT = 30
CELERY_TASK_TIME_LIMIT = 60
CELERY_TASK_RETRY_DELAYS = '1,2,4'

# Mock external services for testing
OPENAI_API_KEY = 'test-openai-key'
PINECONE_API_KEY = 'test-pinecone-key'
STRIPE_SECRET_KEY = 'sk_test_key'
STRIPE_WEBHOOK_SECRET = 'whsec_test_key'

# AWS S3 mocking
AWS_ACCESS_KEY_ID = 'test-access-key'
AWS_SECRET_ACCESS_KEY = 'test-secret-key'
AWS_STORAGE_BUCKET_NAME = 'test-bucket'
AWS_S3_REGION_NAME = 'us-east-1'

# REST Framework configuration  
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "test_staticfiles" 

# Default field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Disable external service connections
ENABLE_SENTRY = False
ENABLE_MONITORING = False
ENABLE_CACHING = True
ENABLE_RATE_LIMITING = False

# Test-specific logging (quieter)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'WARNING',  # Only show warnings and errors during tests
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'], 
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Static files for testing
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Security settings for testing
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
CORS_ALLOW_ALL_ORIGINS = True
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Rate limiting disabled for tests
RATELIMIT_ENABLE = False

# Test-specific chatbot settings
CHATBOT_SETTINGS = {
    'MAX_FILE_SIZE_MB': 10,  # Smaller for tests
    'MAX_EMBEDDING_BATCH_SIZE': 10,
    'OPENAI_API_KEY': 'test-openai-key',
    'OPENAI_MAX_RETRIES': 1,  # Faster failure for tests
    'OPENAI_TIMEOUT': 5,
    'PINECONE_API_KEY': 'test-pinecone-key',
    'PINECONE_ENVIRONMENT': 'test',
    'STRIPE_PUBLISHABLE_KEY': 'pk_test_key',
    'STRIPE_SECRET_KEY': 'sk_test_key',
    'STRIPE_WEBHOOK_SECRET': 'whsec_test_key',
    'AWS_ACCESS_KEY_ID': 'test-access-key',
    'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
    'AWS_STORAGE_BUCKET_NAME': 'test-bucket',
    'AWS_S3_REGION_NAME': 'us-east-1',
}

# Django test runner configuration
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Django test database configuration
if 'test' in sys.argv or 'pytest' in sys.modules:
    # Running in test mode
    DATABASES['default']['NAME'] = ':memory:'