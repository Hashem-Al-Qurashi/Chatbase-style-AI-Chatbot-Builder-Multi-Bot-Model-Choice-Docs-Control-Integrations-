"""
Production-ready Django settings for RAG-based Chatbot SaaS.

This configuration follows senior engineering practices:
- No hardcoding (all configuration from environment)
- Type safety with Pydantic
- Security by design
- Proper error handling
- Observability built-in
"""

from pathlib import Path
import dj_database_url
import structlog
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from .config import get_settings

# Application settings from environment
config = get_settings()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings - environment-based
SECRET_KEY = config.SECRET_KEY
DEBUG = config.DEBUG
ALLOWED_HOSTS = ["*"] if config.is_development else config.get_allowed_hosts()

# Apply security settings based on environment
security_settings = config.get_security_settings_for_environment()
for setting_name, setting_value in security_settings.items():
    globals()[setting_name] = setting_value

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "channels",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_extensions",
]

LOCAL_APPS = [
    # Will be created
    "apps.accounts",
    "apps.chatbots",
    "apps.knowledge",
    "apps.conversations",
    "apps.billing",
    "apps.webhooks",
    "widget",  # Widget app for embeddable chat widgets
]

# Add debug toolbar only in development
if config.ENABLE_DEBUG_TOOLBAR and config.is_development:
    THIRD_PARTY_APPS.append("debug_toolbar")

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Add debug toolbar middleware in development
if config.ENABLE_DEBUG_TOOLBAR and config.is_development:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

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

WSGI_APPLICATION = "chatbot_saas.wsgi.application"
ASGI_APPLICATION = "chatbot_saas.asgi.application"

# Database configuration with connection pooling
DATABASES = {
    "default": dj_database_url.parse(
        config.DATABASE_URL,
        conn_max_age=config.DATABASE_TIMEOUT,
        conn_health_checks=True,
    )
}

# Cache configuration - conditional based on feature flag with Redis fallback
if config.ENABLE_CACHING:
    # Try Redis first, fallback to LocMemCache if Redis unavailable
    try:
        import redis
        redis_client = redis.Redis.from_url(config.REDIS_URL)
        redis_client.ping()  # Test Redis connection
        
        # Redis is available, use it
        CACHES = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": config.REDIS_URL,
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "CONNECTION_POOL_KWARGS": {"max_connections": 50},
                },
                "KEY_PREFIX": "chatbot_saas",
                "TIMEOUT": config.CACHE_TTL_SECONDS,
            }
        }
        SESSION_ENGINE = "django.contrib.sessions.backends.cache"
        SESSION_CACHE_ALIAS = "default"
    except:
        # Redis not available, use in-memory cache
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "chatbot_saas_cache",
                "TIMEOUT": config.CACHE_TTL_SECONDS,
                "OPTIONS": {
                    "MAX_ENTRIES": 10000,  # Limit memory usage
                }
            }
        }
        SESSION_ENGINE = "django.contrib.sessions.backends.db"
else:
    # Use dummy cache and database sessions when caching is disabled
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_SECURE = not config.is_development
SESSION_COOKIE_HTTPONLY = True

# Channel layers configuration for WebSocket support
if config.ENABLE_CACHING:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [config.REDIS_URL],
                "capacity": 1500,  # Maximum messages per channel
                "expiry": 60,      # Message expiry in seconds
            },
        },
    }
else:
    # Use in-memory channel layer for development without Redis
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
SESSION_COOKIE_SAMESITE = "Lax"

# Authentication
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Django Allauth configuration
SITE_ID = 1
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Social account providers
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "APP": {
            "client_id": config.GOOGLE_OAUTH_CLIENT_ID,
            "secret": config.GOOGLE_OAUTH_CLIENT_SECRET,
        },
    }
}

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# Add advanced throttling if rate limiting is enabled
if config.ENABLE_RATE_LIMITING:
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [
        "apps.core.throttling.EndpointSpecificThrottle",
        "apps.core.throttling.PlanBasedUserThrottle", 
        "apps.core.throttling.AbuseDetectionThrottle",
        "rest_framework.throttling.AnonRateThrottle",  # Fallback
        "rest_framework.throttling.UserRateThrottle",  # Fallback
    ]
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        "anon": "100/hour",
        "user": "1000/hour",
        "endpoint_specific": "vary",  # Varies by endpoint and plan
        "plan_based": "vary",  # Varies by user plan
        "abuse_detection": "10/min",  # Anti-abuse limit
    }

# Spectacular (OpenAPI documentation)
SPECTACULAR_SETTINGS = {
    "TITLE": "Chatbot SaaS API",
    "DESCRIPTION": "Enterprise RAG-based chatbot builder with advanced privacy controls, analytics, and seamless integrations. Build, deploy, and scale AI-powered conversational experiences.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {
        "name": "API Support",
        "email": "api-support@yourdomain.com",
    },
    "LICENSE": {
        "name": "Commercial License",
    },
    "TAGS": [
        {"name": "Authentication", "description": "User authentication and OAuth2"},
        {"name": "Chatbots", "description": "Chatbot management and configuration"},
        {"name": "Conversations", "description": "Chat conversations and messaging"},
        {"name": "Knowledge", "description": "Knowledge base and document management"},
        {"name": "Billing", "description": "Subscription and payment management"},
        {"name": "Webhooks", "description": "External integration webhooks"},
        {"name": "Public", "description": "Public endpoints for chat widget"},
    ],
    "SERVERS": [
        {"url": "https://api.yourdomain.com", "description": "Production server"},
        {"url": "https://staging-api.yourdomain.com", "description": "Staging server"},
        {"url": "http://localhost:8000", "description": "Development server"},
    ],
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
}

# CORS configuration
CORS_ALLOWED_ORIGINS = config.get_cors_origins()
CORS_ALLOW_CREDENTIALS = config.CORS_ALLOW_CREDENTIALS
CORS_ALLOW_ALL_ORIGINS = config.is_development

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static and media files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = config.MAX_FILE_SIZE_MB * 1024 * 1024

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery configuration
CELERY_BROKER_URL = config.REDIS_URL
CELERY_RESULT_BACKEND = config.REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "maxBytes": 1024 * 1024 * 15,  # 15MB
            "backupCount": 10,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": config.LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": config.LOG_LEVEL,
            "propagate": False,
        },
        "chatbot_saas": {
            "handlers": ["console", "file"],
            "level": config.LOG_LEVEL,
            "propagate": False,
        },
    },
}

# Structured logging with structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Sentry configuration for error tracking
if config.ENABLE_SENTRY and config.SENTRY_DSN:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_capture=True,
                middleware_spans=True,
                signals_spans=True,
                cache_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
        ],
        traces_sample_rate=1.0 if config.is_development else 0.1,
        send_default_pii=False,
        environment=config.ENVIRONMENT,
    )

# Security settings
if not config.is_development:
    # HTTPS settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    
    # Security headers
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
    
    # Cookie security
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# Debug toolbar configuration
if config.ENABLE_DEBUG_TOOLBAR and config.is_development:
    INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Rate limiting configuration
RATELIMIT_ENABLE = config.ENABLE_RATE_LIMITING
if config.ENABLE_RATE_LIMITING:
    RATELIMIT_USE_CACHE = "default"
else:
    RATELIMIT_USE_CACHE = None

# Custom application settings
CHATBOT_SETTINGS = {
    "MAX_FILE_SIZE_MB": config.MAX_FILE_SIZE_MB,
    "MAX_EMBEDDING_BATCH_SIZE": config.MAX_EMBEDDING_BATCH_SIZE,
    "OPENAI_API_KEY": config.OPENAI_API_KEY,
    "OPENAI_MAX_RETRIES": config.OPENAI_MAX_RETRIES,
    "OPENAI_TIMEOUT": config.OPENAI_TIMEOUT,
    "PINECONE_API_KEY": config.PINECONE_API_KEY,
    "PINECONE_ENVIRONMENT": config.PINECONE_ENVIRONMENT,
    "STRIPE_PUBLISHABLE_KEY": config.STRIPE_PUBLISHABLE_KEY,
    "STRIPE_SECRET_KEY": config.STRIPE_SECRET_KEY,
    "STRIPE_WEBHOOK_SECRET": config.STRIPE_WEBHOOK_SECRET,
    "AWS_ACCESS_KEY_ID": config.AWS_ACCESS_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": config.AWS_SECRET_ACCESS_KEY,
    "AWS_STORAGE_BUCKET_NAME": config.AWS_STORAGE_BUCKET_NAME,
    "AWS_S3_REGION_NAME": config.AWS_S3_REGION_NAME,
}

# Celery Configuration
CELERY_BROKER_URL = config.CELERY_BROKER_URL
CELERY_RESULT_BACKEND = config.CELERY_RESULT_BACKEND
CELERY_TASK_ALWAYS_EAGER = config.CELERY_TASK_ALWAYS_EAGER
CELERY_TASK_EAGER_PROPAGATES = config.CELERY_TASK_EAGER_PROPAGATES
CELERY_TASK_SERIALIZER = config.CELERY_TASK_SERIALIZER
CELERY_RESULT_SERIALIZER = config.CELERY_RESULT_SERIALIZER
CELERY_ACCEPT_CONTENT = [config.CELERY_ACCEPT_CONTENT]
CELERY_TIMEZONE = config.CELERY_TIMEZONE
CELERY_ENABLE_UTC = config.CELERY_ENABLE_UTC

# Celery Worker Configuration
CELERY_WORKER_CONCURRENCY = config.CELERY_WORKER_CONCURRENCY
CELERY_WORKER_MAX_TASKS_PER_CHILD = config.CELERY_WORKER_MAX_TASKS_PER_CHILD
CELERY_WORKER_MAX_MEMORY_PER_CHILD = config.CELERY_WORKER_MAX_MEMORY_PER_CHILD

# Celery Task Configuration
CELERY_TASK_SOFT_TIME_LIMIT = config.CELERY_TASK_SOFT_TIME_LIMIT
CELERY_TASK_TIME_LIMIT = config.CELERY_TASK_TIME_LIMIT
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Parse retry delays from config string
CELERY_TASK_RETRY_DELAYS = [int(x.strip()) for x in config.CELERY_TASK_RETRY_DELAYS.split(',')]

# Development/Testing overrides
if config.is_development or config.is_testing:
    CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously in development
    CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions in development
