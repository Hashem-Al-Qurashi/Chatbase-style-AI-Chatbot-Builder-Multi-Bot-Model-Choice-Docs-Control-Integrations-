"""
Enterprise monitoring and error handling for Celery task pipeline.
Provides metrics, logging, alerting, and health checks.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone
from celery import current_app
from celery.events.state import State
from celery.events import Event

from chatbot_saas.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to track."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class TaskMetric:
    """Individual task performance metric."""
    task_name: str
    task_id: str
    status: str
    duration_ms: float
    timestamp: datetime
    worker_name: str
    retries: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """System alert."""
    level: AlertLevel
    message: str
    timestamp: datetime
    component: str
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates task metrics."""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.task_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.performance_stats = defaultdict(list)
        self._lock = threading.Lock()
    
    def record_task_metric(self, metric: TaskMetric):
        """Record a task performance metric."""
        with self._lock:
            self.metrics.append(metric)
            self.task_counts[metric.task_name] += 1
            
            if metric.status == 'FAILURE':
                self.error_counts[metric.task_name] += 1
            
            if metric.duration_ms > 0:
                self.performance_stats[metric.task_name].append(metric.duration_ms)
                # Keep only last 1000 measurements per task
                if len(self.performance_stats[metric.task_name]) > 1000:
                    self.performance_stats[metric.task_name] = \
                        self.performance_stats[metric.task_name][-1000:]
    
    def get_task_summary(self, task_name: str) -> Dict[str, Any]:
        """Get performance summary for a specific task."""
        with self._lock:
            recent_metrics = [m for m in self.metrics 
                            if m.task_name == task_name 
                            and m.timestamp > timezone.now() - timedelta(hours=1)]
            
            durations = self.performance_stats.get(task_name, [])
            
            summary = {
                "total_executions": self.task_counts.get(task_name, 0),
                "total_errors": self.error_counts.get(task_name, 0),
                "recent_executions": len(recent_metrics),
                "error_rate": 0.0,
                "avg_duration_ms": 0.0,
                "p95_duration_ms": 0.0,
                "p99_duration_ms": 0.0
            }
            
            if recent_metrics:
                errors = sum(1 for m in recent_metrics if m.status == 'FAILURE')
                summary["error_rate"] = errors / len(recent_metrics) * 100
            
            if durations:
                summary["avg_duration_ms"] = sum(durations) / len(durations)
                sorted_durations = sorted(durations)
                summary["p95_duration_ms"] = sorted_durations[int(0.95 * len(sorted_durations))]
                summary["p99_duration_ms"] = sorted_durations[int(0.99 * len(sorted_durations))]
            
            return summary
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        with self._lock:
            now = timezone.now()
            last_hour = now - timedelta(hours=1)
            last_minute = now - timedelta(minutes=1)
            
            recent_metrics = [m for m in self.metrics if m.timestamp > last_hour]
            very_recent = [m for m in self.metrics if m.timestamp > last_minute]
            
            total_tasks = len(recent_metrics)
            failed_tasks = sum(1 for m in recent_metrics if m.status == 'FAILURE')
            
            health = {
                "overall_status": "healthy",
                "tasks_last_hour": total_tasks,
                "tasks_last_minute": len(very_recent),
                "error_rate_last_hour": (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "active_workers": len(set(m.worker_name for m in very_recent)),
                "unique_tasks": len(set(m.task_name for m in recent_metrics)),
                "timestamp": now.isoformat()
            }
            
            # Determine overall health status
            error_rate = health["error_rate_last_hour"]
            if error_rate > 50:
                health["overall_status"] = "critical"
            elif error_rate > 20:
                health["overall_status"] = "degraded"
            elif error_rate > 5:
                health["overall_status"] = "warning"
            
            return health


class AlertManager:
    """Manages system alerts and notifications."""
    
    def __init__(self, max_alerts: int = 1000):
        self.alerts: deque = deque(maxlen=max_alerts)
        self.alert_counts = defaultdict(int)
        self._lock = threading.Lock()
    
    def create_alert(
        self, 
        level: AlertLevel, 
        message: str, 
        component: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create and store an alert."""
        alert = Alert(
            level=level,
            message=message,
            timestamp=timezone.now(),
            component=component,
            task_id=task_id,
            metadata=metadata or {}
        )
        
        with self._lock:
            self.alerts.append(alert)
            self.alert_counts[level] += 1
        
        # Log the alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }[level]
        
        logger.log(log_level, f"[{component}] {message}", extra={
            'task_id': task_id,
            'alert_level': level.value,
            'metadata': metadata
        })
        
        # Send notifications for critical alerts
        if level == AlertLevel.CRITICAL:
            self._send_critical_notification(alert)
        
        return alert
    
    def _send_critical_notification(self, alert: Alert):
        """Send notification for critical alerts."""
        # In production, this would integrate with:
        # - Slack/Teams webhooks
        # - PagerDuty
        # - Email notifications
        # - SMS alerts
        
        logger.critical(f"CRITICAL ALERT: {alert.message} in {alert.component}")
        
        # Store in cache for immediate retrieval
        cache.set(
            f"critical_alert:{alert.timestamp.timestamp()}", 
            {
                'message': alert.message,
                'component': alert.component,
                'timestamp': alert.timestamp.isoformat(),
                'task_id': alert.task_id
            },
            timeout=3600  # 1 hour
        )
    
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get alerts from the last N hours."""
        cutoff = timezone.now() - timedelta(hours=hours)
        with self._lock:
            return [alert for alert in self.alerts if alert.timestamp > cutoff]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert counts by level."""
        recent_alerts = self.get_recent_alerts(24)
        
        summary = {
            "total_alerts_24h": len(recent_alerts),
            "by_level": {level.value: 0 for level in AlertLevel},
            "by_component": defaultdict(int),
            "timestamp": timezone.now().isoformat()
        }
        
        for alert in recent_alerts:
            summary["by_level"][alert.level.value] += 1
            summary["by_component"][alert.component] += 1
        
        return summary


class TaskMonitor:
    """Monitors Celery task execution and performance."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.thresholds = {
            'max_task_duration_ms': 300000,  # 5 minutes
            'max_error_rate_percent': 10,
            'max_queue_size': 1000,
            'min_workers': 1
        }
    
    def record_task_start(self, task_id: str, task_name: str, worker_name: str):
        """Record task start event."""
        cache.set(f"task_start:{task_id}", {
            'start_time': time.time(),
            'task_name': task_name,
            'worker_name': worker_name
        }, timeout=3600)
    
    def record_task_complete(
        self, 
        task_id: str, 
        task_name: str, 
        status: str,
        worker_name: str,
        retries: int = 0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record task completion event."""
        start_data = cache.get(f"task_start:{task_id}")
        if not start_data:
            logger.warning(f"No start data found for task {task_id}")
            duration_ms = 0
        else:
            duration_ms = (time.time() - start_data['start_time']) * 1000
        
        # Create metric
        metric = TaskMetric(
            task_name=task_name,
            task_id=task_id,
            status=status,
            duration_ms=duration_ms,
            timestamp=timezone.now(),
            worker_name=worker_name,
            retries=retries,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        self.metrics_collector.record_task_metric(metric)
        
        # Check for alerts
        self._check_task_alerts(metric)
        
        # Cleanup
        cache.delete(f"task_start:{task_id}")
    
    def _check_task_alerts(self, metric: TaskMetric):
        """Check if task metric triggers any alerts."""
        # Duration alert
        if metric.duration_ms > self.thresholds['max_task_duration_ms']:
            self.alert_manager.create_alert(
                AlertLevel.WARNING,
                f"Task {metric.task_name} took {metric.duration_ms:.0f}ms (>{self.thresholds['max_task_duration_ms']}ms)",
                "task_performance",
                task_id=metric.task_id,
                metadata={'duration_ms': metric.duration_ms}
            )
        
        # Failure alert
        if metric.status == 'FAILURE':
            level = AlertLevel.ERROR if metric.retries < 3 else AlertLevel.CRITICAL
            self.alert_manager.create_alert(
                level,
                f"Task {metric.task_name} failed: {metric.error_message or 'Unknown error'}",
                "task_execution",
                task_id=metric.task_id,
                metadata={'retries': metric.retries, 'error': metric.error_message}
            )
        
        # High retry count alert
        if metric.retries >= 2:
            self.alert_manager.create_alert(
                AlertLevel.WARNING,
                f"Task {metric.task_name} has high retry count: {metric.retries}",
                "task_reliability",
                task_id=metric.task_id,
                metadata={'retries': metric.retries}
            )
    
    def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        health = self.metrics_collector.get_system_health()
        
        # Check error rate
        if health["error_rate_last_hour"] > self.thresholds['max_error_rate_percent']:
            self.alert_manager.create_alert(
                AlertLevel.CRITICAL,
                f"High error rate: {health['error_rate_last_hour']:.1f}% (>{self.thresholds['max_error_rate_percent']}%)",
                "system_health",
                metadata={'error_rate': health["error_rate_last_hour"]}
            )
        
        # Check worker count
        if health["active_workers"] < self.thresholds['min_workers']:
            self.alert_manager.create_alert(
                AlertLevel.CRITICAL,
                f"Insufficient workers: {health['active_workers']} (<{self.thresholds['min_workers']})",
                "worker_availability",
                metadata={'active_workers': health["active_workers"]}
            )
        
        # Add alert summary to health
        health["alerts"] = self.alert_manager.get_alert_summary()
        
        return health
    
    def get_task_analytics(self, task_name: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed task analytics."""
        if task_name:
            return {
                "task_name": task_name,
                "summary": self.metrics_collector.get_task_summary(task_name),
                "recent_alerts": [
                    alert for alert in self.alert_manager.get_recent_alerts(24)
                    if task_name in alert.message or alert.task_id
                ]
            }
        else:
            # Get analytics for all tasks
            all_tasks = set()
            for metric in self.metrics_collector.metrics:
                all_tasks.add(metric.task_name)
            
            return {
                "all_tasks": {
                    task: self.metrics_collector.get_task_summary(task)
                    for task in all_tasks
                },
                "system_health": self.check_system_health(),
                "alert_summary": self.alert_manager.get_alert_summary()
            }


# Global monitor instance
task_monitor = TaskMonitor()


def get_monitoring_dashboard() -> Dict[str, Any]:
    """Get comprehensive monitoring dashboard data."""
    return {
        "system_health": task_monitor.check_system_health(),
        "task_analytics": task_monitor.get_task_analytics(),
        "recent_alerts": [
            {
                "level": alert.level.value,
                "message": alert.message,
                "component": alert.component,
                "timestamp": alert.timestamp.isoformat(),
                "task_id": alert.task_id
            }
            for alert in task_monitor.alert_manager.get_recent_alerts(24)
        ],
        "timestamp": timezone.now().isoformat()
    }


def export_metrics_json() -> str:
    """Export metrics in JSON format for external monitoring systems."""
    dashboard_data = get_monitoring_dashboard()
    return json.dumps(dashboard_data, indent=2, default=str)


# Health check endpoint data
def track_metric(metric_name: str, value: float, tags: Dict[str, str] = None) -> None:
    """
    Track a metric for monitoring and observability.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        tags: Optional tags for the metric
    """
    # Simple implementation for now - could be enhanced with actual monitoring
    logger.info(f"METRIC: {metric_name} = {value}", extra={"tags": tags or {}})


# Create global monitoring instances
metrics_collector = MetricsCollector()
alert_manager = AlertManager()


def get_health_check() -> Dict[str, Any]:
    """Get simple health check status for load balancers."""
    health = task_monitor.check_system_health()
    
    return {
        "status": health["overall_status"],
        "timestamp": timezone.now().isoformat(),
        "checks": {
            "tasks_processing": health["tasks_last_minute"] > 0,
            "error_rate_ok": health["error_rate_last_hour"] < 20,
            "workers_available": health["active_workers"] > 0
        }
    }