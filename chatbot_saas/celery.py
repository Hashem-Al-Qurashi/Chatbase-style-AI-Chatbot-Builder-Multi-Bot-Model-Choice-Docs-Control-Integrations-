"""
Celery configuration for Django project.
Provides asynchronous task processing for document pipeline.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

app = Celery('chatbot_saas')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery beat configuration for periodic tasks
app.conf.beat_schedule = {
    'cleanup-expired-sessions': {
        'task': 'apps.core.tasks.cleanup_expired_sessions',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-temporary-files': {
        'task': 'apps.core.tasks.cleanup_temporary_files',
        'schedule': 1800.0,  # Every 30 minutes
    },
    'monitor-embedding-costs': {
        'task': 'apps.core.tasks.monitor_embedding_costs',
        'schedule': 300.0,  # Every 5 minutes
    },
}

app.conf.timezone = 'UTC'

# Task routing configuration
app.conf.task_routes = {
    'apps.core.tasks.process_document_pipeline': {'queue': 'documents'},
    'apps.core.tasks.generate_embeddings_task': {'queue': 'embeddings'},
    'apps.core.tasks.store_vectors_task': {'queue': 'vectors'},
    'apps.core.tasks.cleanup_*': {'queue': 'maintenance'},
}

# Task priority configuration
app.conf.task_inherit_parent_priority = True
app.conf.task_default_priority = 5  # Medium priority
app.conf.worker_prefetch_multiplier = 4

# Result backend configuration
app.conf.result_backend = settings.CELERY_RESULT_BACKEND
app.conf.result_expires = 3600  # 1 hour

# Task serialization
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']

# Worker configuration
app.conf.worker_max_tasks_per_child = 1000
app.conf.worker_max_memory_per_child = 200000  # 200MB

# Retry configuration
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery functionality."""
    print(f'Request: {self.request!r}')