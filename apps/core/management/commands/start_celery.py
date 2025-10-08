"""
Django management command to start Celery worker with proper configuration.
"""

import os
import subprocess
import sys
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from chatbot_saas.config import get_settings


class Command(BaseCommand):
    help = 'Start Celery worker with proper configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--concurrency',
            type=int,
            default=None,
            help='Number of concurrent worker processes'
        )
        parser.add_argument(
            '--loglevel',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            default='INFO',
            help='Logging level (default: INFO)'
        )
        parser.add_argument(
            '--queues',
            type=str,
            default='celery',
            help='Comma-separated list of queues to consume from'
        )
        parser.add_argument(
            '--beat',
            action='store_true',
            help='Also start Celery Beat scheduler'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show command that would be executed without running it'
        )

    def handle(self, *args, **options):
        config = get_settings()
        
        # Build celery worker command
        cmd = ['celery', '-A', 'chatbot_saas', 'worker']
        
        # Add concurrency
        concurrency = options['concurrency'] or config.CELERY_WORKER_CONCURRENCY
        cmd.extend(['--concurrency', str(concurrency)])
        
        # Add log level
        cmd.extend(['--loglevel', options['loglevel']])
        
        # Add queues
        cmd.extend(['--queues', options['queues']])
        
        # Add additional worker options
        cmd.extend([
            '--time-limit', str(config.CELERY_TASK_TIME_LIMIT),
            '--soft-time-limit', str(config.CELERY_TASK_SOFT_TIME_LIMIT),
            '--max-tasks-per-child', str(config.CELERY_WORKER_MAX_TASKS_PER_CHILD),
            '--max-memory-per-child', str(config.CELERY_WORKER_MAX_MEMORY_PER_CHILD)
        ])
        
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS("Would execute: " + " ".join(cmd))
            )
            
            if options['beat']:
                beat_cmd = ['celery', '-A', 'chatbot_saas', 'beat', '--loglevel', options['loglevel']]
                self.stdout.write(
                    self.style.SUCCESS("Would also execute: " + " ".join(beat_cmd))
                )
            return
        
        # Check if Redis is available
        self.check_redis_connection()
        
        # Check if Django settings are properly configured
        self.check_django_config()
        
        # Start Celery Beat if requested (in background)
        if options['beat']:
            self.start_celery_beat(options['loglevel'])
        
        # Display startup information
        self.display_startup_info(config, options)
        
        # Start the worker
        try:
            self.stdout.write(
                self.style.SUCCESS("Starting Celery worker...")
            )
            self.stdout.write("Press Ctrl+C to stop")
            
            # Execute celery worker
            subprocess.run(cmd, check=True)
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS("\nCelery worker stopped.")
            )
        except subprocess.CalledProcessError as e:
            raise CommandError(f"Celery worker failed to start: {e}")
        except FileNotFoundError:
            raise CommandError(
                "Celery not found. Install it with: pip install celery[redis]"
            )

    def check_redis_connection(self):
        """Check if Redis is available."""
        try:
            from django.core.cache import cache
            cache.set('health_check', 'test', 10)
            if cache.get('health_check') != 'test':
                raise Exception("Cache write/read failed")
            cache.delete('health_check')
            
            self.stdout.write(
                self.style.SUCCESS("✓ Redis connection OK")
            )
        except Exception as e:
            raise CommandError(
                f"Redis connection failed: {e}\n"
                "Make sure Redis is running and properly configured."
            )

    def check_django_config(self):
        """Check Django configuration."""
        required_settings = [
            'CELERY_BROKER_URL',
            'CELERY_RESULT_BACKEND'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing_settings.append(setting)
        
        if missing_settings:
            raise CommandError(
                f"Missing required settings: {', '.join(missing_settings)}"
            )
        
        self.stdout.write(
            self.style.SUCCESS("✓ Django configuration OK")
        )

    def start_celery_beat(self, loglevel):
        """Start Celery Beat scheduler in background."""
        beat_cmd = [
            'celery', '-A', 'chatbot_saas', 'beat',
            '--loglevel', loglevel,
            '--detach'
        ]
        
        try:
            subprocess.run(beat_cmd, check=True)
            self.stdout.write(
                self.style.SUCCESS("✓ Celery Beat scheduler started")
            )
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.WARNING(f"Failed to start Celery Beat: {e}")
            )

    def display_startup_info(self, config, options):
        """Display startup information."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("CELERY WORKER CONFIGURATION")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Environment: {config.ENVIRONMENT}")
        self.stdout.write(f"Debug Mode: {config.DEBUG}")
        self.stdout.write(f"Broker URL: {config.CELERY_BROKER_URL}")
        self.stdout.write(f"Result Backend: {config.CELERY_RESULT_BACKEND}")
        self.stdout.write(f"Concurrency: {options['concurrency'] or config.CELERY_WORKER_CONCURRENCY}")
        self.stdout.write(f"Log Level: {options['loglevel']}")
        self.stdout.write(f"Queues: {options['queues']}")
        self.stdout.write(f"Task Time Limit: {config.CELERY_TASK_TIME_LIMIT}s")
        self.stdout.write(f"Max Tasks Per Child: {config.CELERY_WORKER_MAX_TASKS_PER_CHILD}")
        
        if config.CELERY_TASK_ALWAYS_EAGER:
            self.stdout.write(
                self.style.WARNING("⚠ CELERY_TASK_ALWAYS_EAGER=True (tasks run synchronously)")
            )
        
        self.stdout.write("=" * 60 + "\n")