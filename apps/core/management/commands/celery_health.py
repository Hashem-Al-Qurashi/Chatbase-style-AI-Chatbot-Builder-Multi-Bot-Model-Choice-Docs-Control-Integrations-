"""
Django management command to check Celery system health and monitoring status.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import json

from apps.core.monitoring import get_monitoring_dashboard, get_health_check


class Command(BaseCommand):
    help = 'Check Celery system health and display monitoring information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['human', 'json'],
            default='human',
            help='Output format (default: human)'
        )
        parser.add_argument(
            '--brief',
            action='store_true',
            help='Show brief health check only'
        )

    def handle(self, *args, **options):
        if options['brief']:
            self.show_brief_health(options['format'])
        else:
            self.show_full_dashboard(options['format'])

    def show_brief_health(self, format_type):
        """Show brief health check status."""
        try:
            health = get_health_check()
            
            if format_type == 'json':
                self.stdout.write(json.dumps(health, indent=2))
                return
            
            # Human readable format
            status = health['status']
            status_color = {
                'healthy': self.style.SUCCESS,
                'warning': self.style.WARNING,
                'degraded': self.style.WARNING,
                'critical': self.style.ERROR,
                'unhealthy': self.style.ERROR
            }.get(status, self.style.NOTICE)
            
            self.stdout.write(
                status_color(f"System Status: {status.upper()}")
            )
            
            self.stdout.write("\nHealth Checks:")
            for check_name, check_result in health['checks'].items():
                check_status = "✓" if check_result else "✗"
                check_color = self.style.SUCCESS if check_result else self.style.ERROR
                self.stdout.write(
                    f"  {check_color(check_status)} {check_name.replace('_', ' ').title()}"
                )
            
            self.stdout.write(f"\nChecked at: {health['timestamp']}")
            
        except Exception as e:
            raise CommandError(f"Failed to get health status: {str(e)}")

    def show_full_dashboard(self, format_type):
        """Show full monitoring dashboard."""
        try:
            dashboard = get_monitoring_dashboard()
            
            if format_type == 'json':
                self.stdout.write(json.dumps(dashboard, indent=2))
                return
            
            # Human readable format
            system_health = dashboard['system_health']
            task_analytics = dashboard['task_analytics']
            recent_alerts = dashboard['recent_alerts']
            
            # System Health Section
            self.stdout.write(
                self.style.HTTP_INFO("=" * 60)
            )
            self.stdout.write(
                self.style.HTTP_INFO("CELERY SYSTEM MONITORING DASHBOARD")
            )
            self.stdout.write(
                self.style.HTTP_INFO("=" * 60)
            )
            
            status = system_health['overall_status']
            status_color = {
                'healthy': self.style.SUCCESS,
                'warning': self.style.WARNING,
                'degraded': self.style.WARNING,
                'critical': self.style.ERROR,
                'unhealthy': self.style.ERROR
            }.get(status, self.style.NOTICE)
            
            self.stdout.write(f"\nSystem Status: {status_color(status.upper())}")
            self.stdout.write(f"Tasks Last Hour: {system_health['tasks_last_hour']}")
            self.stdout.write(f"Tasks Last Minute: {system_health['tasks_last_minute']}")
            self.stdout.write(f"Error Rate (1h): {system_health['error_rate_last_hour']:.1f}%")
            self.stdout.write(f"Active Workers: {system_health['active_workers']}")
            self.stdout.write(f"Unique Task Types: {system_health['unique_tasks']}")
            
            # Task Analytics Section
            if 'all_tasks' in task_analytics:
                self.stdout.write(f"\n{self.style.HTTP_INFO('TASK ANALYTICS:')}")
                for task_name, stats in task_analytics['all_tasks'].items():
                    self.stdout.write(f"\n  {self.style.WARNING(task_name)}:")
                    self.stdout.write(f"    Total Executions: {stats['total_executions']}")
                    self.stdout.write(f"    Total Errors: {stats['total_errors']}")
                    self.stdout.write(f"    Recent Executions: {stats['recent_executions']}")
                    self.stdout.write(f"    Error Rate: {stats['error_rate']:.1f}%")
                    self.stdout.write(f"    Avg Duration: {stats['avg_duration_ms']:.0f}ms")
                    if stats['p95_duration_ms'] > 0:
                        self.stdout.write(f"    P95 Duration: {stats['p95_duration_ms']:.0f}ms")
            
            # Alerts Section
            if recent_alerts:
                self.stdout.write(f"\n{self.style.HTTP_INFO('RECENT ALERTS (24h):')}")
                for alert in recent_alerts[-10:]:  # Show last 10 alerts
                    level = alert['level']
                    level_color = {
                        'info': self.style.NOTICE,
                        'warning': self.style.WARNING,
                        'error': self.style.ERROR,
                        'critical': self.style.ERROR
                    }.get(level, self.style.NOTICE)
                    
                    self.stdout.write(
                        f"  {level_color(f'[{level.upper()}]')} "
                        f"{alert['message']} "
                        f"({alert['component']}) "
                        f"- {alert['timestamp']}"
                    )
            else:
                self.stdout.write(f"\n{self.style.SUCCESS('No recent alerts')}")
            
            # Alert Summary
            if 'alerts' in system_health:
                alert_summary = system_health['alerts']
                self.stdout.write(f"\n{self.style.HTTP_INFO('ALERT SUMMARY (24h):')}")
                for level, count in alert_summary['by_level'].items():
                    if count > 0:
                        level_color = {
                            'info': self.style.NOTICE,
                            'warning': self.style.WARNING,
                            'error': self.style.ERROR,
                            'critical': self.style.ERROR
                        }.get(level, self.style.NOTICE)
                        self.stdout.write(f"  {level_color(level.upper())}: {count}")
            
            self.stdout.write(f"\n{self.style.HTTP_INFO('=' * 60)}")
            self.stdout.write(f"Generated at: {dashboard['timestamp']}")
            
        except Exception as e:
            raise CommandError(f"Failed to get monitoring dashboard: {str(e)}")