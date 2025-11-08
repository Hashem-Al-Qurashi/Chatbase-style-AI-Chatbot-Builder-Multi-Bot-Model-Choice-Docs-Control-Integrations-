"""
Configuration management using Pydantic BaseSettings.
This ensures no hardcoding and type-safe configuration.
"""
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings with type validation and environment-based configuration."""
    
    # Environment
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(True, env="DEBUG")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(20, env="DATABASE_POOL_SIZE")
    DATABASE_TIMEOUT: int = Field(30, env="DATABASE_TIMEOUT")
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MAX_RETRIES: int = Field(3, env="OPENAI_MAX_RETRIES")
    OPENAI_TIMEOUT: int = Field(30, env="OPENAI_TIMEOUT")
    OPENAI_BASE_URL: str = Field("https://api.openai.com/v1", env="OPENAI_BASE_URL")
    
    # Pinecone
    PINECONE_API_KEY: str = Field(..., env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = Field("us-west1-gcp", env="PINECONE_ENVIRONMENT")
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = Field(..., env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(..., env="AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME: str = Field(..., env="AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME: str = Field("us-east-1", env="AWS_S3_REGION_NAME")
    
    # Stripe
    STRIPE_PUBLISHABLE_KEY: str = Field(..., env="STRIPE_PUBLISHABLE_KEY")
    STRIPE_SECRET_KEY: str = Field(..., env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(..., env="STRIPE_WEBHOOK_SECRET")
    
    # Celery / Redis
    CELERY_BROKER_URL: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379/1", env="CELERY_RESULT_BACKEND")
    CELERY_TASK_ALWAYS_EAGER: bool = Field(False, env="CELERY_TASK_ALWAYS_EAGER")
    CELERY_TASK_EAGER_PROPAGATES: bool = Field(True, env="CELERY_TASK_EAGER_PROPAGATES")
    CELERY_TASK_SERIALIZER: str = Field("json", env="CELERY_TASK_SERIALIZER")
    CELERY_RESULT_SERIALIZER: str = Field("json", env="CELERY_RESULT_SERIALIZER")
    CELERY_ACCEPT_CONTENT: str = Field("json", env="CELERY_ACCEPT_CONTENT")
    CELERY_TIMEZONE: str = Field("UTC", env="CELERY_TIMEZONE")
    CELERY_ENABLE_UTC: bool = Field(True, env="CELERY_ENABLE_UTC")
    CELERY_WORKER_CONCURRENCY: int = Field(2, env="CELERY_WORKER_CONCURRENCY")
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = Field(1000, env="CELERY_WORKER_MAX_TASKS_PER_CHILD")
    CELERY_WORKER_MAX_MEMORY_PER_CHILD: int = Field(200000, env="CELERY_WORKER_MAX_MEMORY_PER_CHILD")  # 200MB
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(300, env="CELERY_TASK_SOFT_TIME_LIMIT")  # 5 minutes
    CELERY_TASK_TIME_LIMIT: int = Field(600, env="CELERY_TASK_TIME_LIMIT")  # 10 minutes
    CELERY_TASK_RETRY_DELAYS: str = Field("60,120,300", env="CELERY_TASK_RETRY_DELAYS")  # Retry delays in seconds
    
    # Security
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_LIFETIME: int = Field(900, env="JWT_ACCESS_TOKEN_LIFETIME")  # 15 minutes
    JWT_REFRESH_TOKEN_LIFETIME: int = Field(604800, env="JWT_REFRESH_TOKEN_LIFETIME")  # 7 days
    
    # Django Security Settings
    SECURE_HSTS_SECONDS: int = Field(31536000, env="SECURE_HSTS_SECONDS")  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = Field(True, env="SECURE_HSTS_INCLUDE_SUBDOMAINS")
    SECURE_HSTS_PRELOAD: bool = Field(True, env="SECURE_HSTS_PRELOAD")
    SECURE_SSL_REDIRECT: bool = Field(True, env="SECURE_SSL_REDIRECT")
    SECURE_PROXY_SSL_HEADER: tuple = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_CONTENT_TYPE_NOSNIFF: bool = Field(True, env="SECURE_CONTENT_TYPE_NOSNIFF")
    SECURE_BROWSER_XSS_FILTER: bool = Field(True, env="SECURE_BROWSER_XSS_FILTER")
    SECURE_REFERRER_POLICY: str = Field("strict-origin-when-cross-origin", env="SECURE_REFERRER_POLICY")
    
    # Cookie Security
    SESSION_COOKIE_SECURE: bool = Field(True, env="SESSION_COOKIE_SECURE")
    SESSION_COOKIE_HTTPONLY: bool = Field(True, env="SESSION_COOKIE_HTTPONLY")
    SESSION_COOKIE_SAMESITE: str = Field("Lax", env="SESSION_COOKIE_SAMESITE")
    CSRF_COOKIE_SECURE: bool = Field(True, env="CSRF_COOKIE_SECURE")
    CSRF_COOKIE_HTTPONLY: bool = Field(True, env="CSRF_COOKIE_HTTPONLY")
    CSRF_COOKIE_SAMESITE: str = Field("Lax", env="CSRF_COOKIE_SAMESITE")
    
    # Frame Options
    X_FRAME_OPTIONS: str = Field("DENY", env="X_FRAME_OPTIONS")
    
    # Allowed Hosts
    ALLOWED_HOSTS: str = Field("localhost,127.0.0.1", env="ALLOWED_HOSTS")
    
    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID: str = Field(..., env="GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET: str = Field(..., env="GOOGLE_OAUTH_CLIENT_SECRET")
    
    # Feature Flags
    ENABLE_CACHING: bool = Field(True, env="ENABLE_CACHING")
    ENABLE_RATE_LIMITING: bool = Field(True, env="ENABLE_RATE_LIMITING")
    ENABLE_DEBUG_TOOLBAR: bool = Field(False, env="ENABLE_DEBUG_TOOLBAR")
    ENABLE_SENTRY: bool = Field(False, env="ENABLE_SENTRY")
    
    # Performance
    MAX_FILE_SIZE_MB: int = Field(100, env="MAX_FILE_SIZE_MB")
    MAX_EMBEDDING_BATCH_SIZE: int = Field(100, env="MAX_EMBEDDING_BATCH_SIZE")
    CACHE_TTL_SECONDS: int = Field(3600, env="CACHE_TTL_SECONDS")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    PROMETHEUS_METRICS_PORT: int = Field(8001, env="PROMETHEUS_METRICS_PORT")
    
    # CORS
    CORS_ALLOWED_ORIGINS: str = Field("", env="CORS_ALLOWED_ORIGINS")
    CORS_ALLOW_CREDENTIALS: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    
    def get_cors_origins(self) -> List[str]:
        """Parse comma-separated CORS origins."""
        if not self.CORS_ALLOWED_ORIGINS.strip():
            return []
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
    
    def get_allowed_hosts(self) -> List[str]:
        """Parse comma-separated allowed hosts."""
        if not self.ALLOWED_HOSTS.strip():
            return ["localhost", "127.0.0.1"]
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]
    
    def get_security_settings_for_environment(self) -> dict:
        """Get environment-specific security settings."""
        if self.is_development:
            # Relaxed security for development
            return {
                "SECURE_SSL_REDIRECT": False,
                "SECURE_HSTS_SECONDS": 0,
                "SESSION_COOKIE_SECURE": False,
                "CSRF_COOKIE_SECURE": False,
            }
        else:
            # Production security settings
            return {
                "SECURE_SSL_REDIRECT": self.SECURE_SSL_REDIRECT,
                "SECURE_HSTS_SECONDS": self.SECURE_HSTS_SECONDS,
                "SECURE_HSTS_INCLUDE_SUBDOMAINS": self.SECURE_HSTS_INCLUDE_SUBDOMAINS,
                "SECURE_HSTS_PRELOAD": self.SECURE_HSTS_PRELOAD,
                "SECURE_PROXY_SSL_HEADER": self.SECURE_PROXY_SSL_HEADER,
                "SECURE_CONTENT_TYPE_NOSNIFF": self.SECURE_CONTENT_TYPE_NOSNIFF,
                "SECURE_BROWSER_XSS_FILTER": self.SECURE_BROWSER_XSS_FILTER,
                "SECURE_REFERRER_POLICY": self.SECURE_REFERRER_POLICY,
                "SESSION_COOKIE_SECURE": self.SESSION_COOKIE_SECURE,
                "SESSION_COOKIE_HTTPONLY": self.SESSION_COOKIE_HTTPONLY,
                "SESSION_COOKIE_SAMESITE": self.SESSION_COOKIE_SAMESITE,
                "CSRF_COOKIE_SECURE": self.CSRF_COOKIE_SECURE,
                "CSRF_COOKIE_HTTPONLY": self.CSRF_COOKIE_HTTPONLY,
                "CSRF_COOKIE_SAMESITE": self.CSRF_COOKIE_SAMESITE,
                "X_FRAME_OPTIONS": self.X_FRAME_OPTIONS,
            }
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        """Ensure secret key is secure in production."""
        environment = values.get("ENVIRONMENT", "development")
        if environment == "production" and v in ("dev-secret-key-change-in-production", "your-secret-key-here"):
            raise ValueError("SECRET_KEY must be changed in production")
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v, values):
        """Validate database URL format."""
        environment = values.get("ENVIRONMENT", "development")
        
        if environment == "development":
            # Allow SQLite for development
            if not v.startswith(("postgresql://", "postgres://", "sqlite://")):
                raise ValueError("DATABASE_URL must be a valid database connection string")
        else:
            # Require PostgreSQL for production
            if not v.startswith(("postgresql://", "postgres://")):
                raise ValueError("DATABASE_URL must be a PostgreSQL connection string in production")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == "testing"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings.
    
    Returns:
        Settings: Application configuration
    """
    return settings