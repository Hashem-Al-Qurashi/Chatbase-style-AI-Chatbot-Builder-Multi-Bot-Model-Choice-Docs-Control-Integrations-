"""
Health check endpoints for Django RAG Chatbot SaaS.
Provides comprehensive health monitoring for all system components.
"""

import time
import logging
from typing import Dict, Any, List, Tuple
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import redis
import openai
import pinecone
import boto3
from botocore.exceptions import ClientError
import structlog

logger = structlog.get_logger(__name__)

class HealthCheckResult:
    """Result of a health check operation."""
    
    def __init__(self, name: str, healthy: bool, details: Dict[str, Any] = None, 
                 response_time: float = None, error: str = None):
        self.name = name
        self.healthy = healthy
        self.details = details or {}
        self.response_time = response_time
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name,
            'healthy': self.healthy,
            'details': self.details
        }
        
        if self.response_time is not None:
            result['response_time_ms'] = round(self.response_time * 1000, 2)
        
        if self.error:
            result['error'] = self.error
        
        return result


class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'cache': self._check_cache,
            'redis': self._check_redis,
            'openai': self._check_openai,
            'pinecone': self._check_pinecone,
            's3': self._check_s3,
            'celery': self._check_celery,
        }
    
    def run_check(self, check_name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if check_name not in self.checks:
            return HealthCheckResult(
                name=check_name,
                healthy=False,
                error=f"Unknown health check: {check_name}"
            )
        
        start_time = time.time()
        try:
            check_func = self.checks[check_name]
            result = check_func()
            result.response_time = time.time() - start_time
            return result
        except Exception as e:
            logger.error(f"Health check {check_name} failed", error=str(e))
            return HealthCheckResult(
                name=check_name,
                healthy=False,
                error=str(e),
                response_time=time.time() - start_time
            )
    
    def run_all_checks(self) -> List[HealthCheckResult]:
        """Run all health checks."""
        results = []
        for check_name in self.checks.keys():
            results.append(self.run_check(check_name))
        return results
    
    def _check_database(self) -> HealthCheckResult:
        """Check database connectivity and basic operations."""
        try:
            db_conn = connections['default']
            with db_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            # Check connection pool status
            total_queries = db_conn.queries_logged if hasattr(db_conn, 'queries_logged') else 0
            
            return HealthCheckResult(
                name='database',
                healthy=True,
                details={
                    'database': db_conn.settings_dict['NAME'],
                    'vendor': db_conn.vendor,
                    'total_queries': total_queries,
                    'connection_status': 'connected'
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name='database',
                healthy=False,
                error=str(e)
            )
    
    def _check_cache(self) -> HealthCheckResult:
        """Check Django cache functionality."""
        try:
            test_key = 'health_check_test'
            test_value = 'health_check_value'
            
            # Test cache write
            cache.set(test_key, test_value, timeout=60)
            
            # Test cache read
            cached_value = cache.get(test_key)
            
            if cached_value != test_value:
                return HealthCheckResult(
                    name='cache',
                    healthy=False,
                    error='Cache read/write test failed'
                )
            
            # Clean up
            cache.delete(test_key)
            
            return HealthCheckResult(
                name='cache',
                healthy=True,
                details={
                    'backend': str(cache._cache.__class__.__name__),
                    'test_passed': True
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name='cache',
                healthy=False,
                error=str(e)
            )
    
    def _check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity directly."""
        try:
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            
            # Test ping
            pong = r.ping()
            
            # Get Redis info
            info = r.info()
            
            return HealthCheckResult(
                name='redis',
                healthy=True,
                details={
                    'ping': pong,
                    'version': info.get('redis_version'),
                    'connected_clients': info.get('connected_clients'),
                    'used_memory_human': info.get('used_memory_human'),
                    'uptime_in_seconds': info.get('uptime_in_seconds')
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name='redis',
                healthy=False,
                error=str(e)
            )
    
    def _check_openai(self) -> HealthCheckResult:
        """Check OpenAI API connectivity."""
        try:
            if not hasattr(settings, 'CHATBOT_SETTINGS') or not settings.CHATBOT_SETTINGS.get('OPENAI_API_KEY'):
                return HealthCheckResult(
                    name='openai',
                    healthy=False,
                    error='OpenAI API key not configured'
                )
            
            openai.api_key = settings.CHATBOT_SETTINGS['OPENAI_API_KEY']
            
            # Test API connectivity with a minimal request
            models = openai.Model.list()
            
            return HealthCheckResult(
                name='openai',
                healthy=True,
                details={
                    'api_accessible': True,
                    'models_available': len(models.data) if hasattr(models, 'data') else 0
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name='openai',
                healthy=False,
                error=str(e)
            )
    
    def _check_pinecone(self) -> HealthCheckResult:
        """Check Pinecone vector database connectivity."""
        try:
            if not hasattr(settings, 'CHATBOT_SETTINGS') or not settings.CHATBOT_SETTINGS.get('PINECONE_API_KEY'):
                return HealthCheckResult(
                    name='pinecone',
                    healthy=False,
                    error='Pinecone API key not configured'
                )
            
            pinecone.init(
                api_key=settings.CHATBOT_SETTINGS['PINECONE_API_KEY'],
                environment=settings.CHATBOT_SETTINGS.get('PINECONE_ENVIRONMENT', 'us-west1-gcp')
            )
            
            # List indexes to test connectivity
            indexes = pinecone.list_indexes()
            
            return HealthCheckResult(
                name='pinecone',
                healthy=True,
                details={
                    'api_accessible': True,
                    'indexes_available': len(indexes)
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name='pinecone',
                healthy=False,
                error=str(e)
            )
    
    def _check_s3(self) -> HealthCheckResult:
        """Check AWS S3 connectivity."""
        try:
            if not hasattr(settings, 'CHATBOT_SETTINGS'):
                return HealthCheckResult(
                    name='s3',
                    healthy=False,
                    error='AWS S3 not configured'
                )
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.CHATBOT_SETTINGS.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=settings.CHATBOT_SETTINGS.get('AWS_SECRET_ACCESS_KEY'),
                region_name=settings.CHATBOT_SETTINGS.get('AWS_S3_REGION_NAME', 'us-east-1')
            )
            
            bucket_name = settings.CHATBOT_SETTINGS.get('AWS_STORAGE_BUCKET_NAME')
            if not bucket_name:
                return HealthCheckResult(
                    name='s3',
                    healthy=False,
                    error='S3 bucket name not configured'
                )
            
            # Test bucket accessibility
            response = s3_client.head_bucket(Bucket=bucket_name)
            
            return HealthCheckResult(
                name='s3',
                healthy=True,
                details={
                    'bucket': bucket_name,
                    'accessible': True,
                    'region': s3_client.meta.region_name
                }
            )
        except ClientError as e:
            return HealthCheckResult(
                name='s3',
                healthy=False,
                error=f"S3 error: {e.response['Error']['Code']}"
            )
        except Exception as e:
            return HealthCheckResult(
                name='s3',
                healthy=False,
                error=str(e)
            )
    
    def _check_celery(self) -> HealthCheckResult:
        """Check Celery worker connectivity."""
        try:
            from celery import current_app
            
            # Get active workers
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            active = inspect.active()
            
            if not stats:
                return HealthCheckResult(
                    name='celery',
                    healthy=False,
                    error='No Celery workers found'
                )
            
            total_workers = len(stats)
            active_tasks = sum(len(tasks) for tasks in (active or {}).values())
            
            return HealthCheckResult(
                name='celery',
                healthy=True,
                details={
                    'workers_online': total_workers,
                    'active_tasks': active_tasks,
                    'workers': list(stats.keys()) if stats else []
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name='celery',
                healthy=False,
                error=str(e)
            )


# Global health checker instance
health_checker = HealthChecker()


@never_cache
@require_http_methods(["GET"])
def basic_health(request):
    """Basic health check endpoint for load balancers."""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': getattr(settings, 'VERSION', '1.0.0')
    })


@api_view(['GET'])
@permission_classes([AllowAny])
@never_cache
def detailed_health(request):
    """Detailed health check with all system components."""
    results = health_checker.run_all_checks()
    
    overall_healthy = all(result.healthy for result in results)
    response_data = {
        'status': 'healthy' if overall_healthy else 'unhealthy',
        'timestamp': time.time(),
        'version': getattr(settings, 'VERSION', '1.0.0'),
        'checks': [result.to_dict() for result in results],
        'summary': {
            'total_checks': len(results),
            'healthy_checks': sum(1 for r in results if r.healthy),
            'unhealthy_checks': sum(1 for r in results if not r.healthy)
        }
    }
    
    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(response_data, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
@never_cache
def component_health(request, component):
    """Health check for a specific component."""
    result = health_checker.run_check(component)
    
    response_data = {
        'status': 'healthy' if result.healthy else 'unhealthy',
        'timestamp': time.time(),
        'check': result.to_dict()
    }
    
    status_code = status.HTTP_200_OK if result.healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(response_data, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
@never_cache
def readiness_check(request):
    """Kubernetes-style readiness check."""
    # Check only critical components for readiness
    critical_checks = ['database', 'cache', 'redis']
    results = [health_checker.run_check(check) for check in critical_checks]
    
    ready = all(result.healthy for result in results)
    
    response_data = {
        'ready': ready,
        'timestamp': time.time(),
        'checks': [result.to_dict() for result in results]
    }
    
    status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(response_data, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
@never_cache
def liveness_check(request):
    """Kubernetes-style liveness check."""
    # Very basic check - just ensure the application is running
    return Response({
        'alive': True,
        'timestamp': time.time(),
        'pid': os.getpid() if hasattr(os, 'getpid') else None
    })


# Prometheus metrics endpoint
@api_view(['GET'])
@permission_classes([AllowAny])
@never_cache
def metrics(request):
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from django.http import HttpResponse
    
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)