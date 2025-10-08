# Makefile for Django RAG Chatbot SaaS
# Simplifies common development and deployment tasks

.PHONY: help build start stop restart logs shell test lint format security deploy-dev deploy-staging deploy-prod backup restore clean

# Default target
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development Commands
build: ## Build Docker images
	docker-compose build

start: ## Start all services
	docker-compose up -d
	@echo "Services started. Access the application at http://localhost:8000"

stop: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-web: ## View Django application logs
	docker-compose logs -f web

logs-celery: ## View Celery worker logs
	docker-compose logs -f celery

shell: ## Access Django shell
	docker-compose exec web python manage.py shell

dbshell: ## Access database shell
	docker-compose exec web python manage.py dbshell

migrate: ## Run database migrations
	docker-compose exec web python manage.py migrate

migrations: ## Create new migrations
	docker-compose exec web python manage.py makemigrations

superuser: ## Create Django superuser
	docker-compose exec web python manage.py createsuperuser

collectstatic: ## Collect static files
	docker-compose exec web python manage.py collectstatic --noinput

# Testing and Quality
test: ## Run test suite
	docker-compose exec web python -m pytest -v --cov=apps --cov=chatbot_saas

test-fast: ## Run tests with fast settings
	docker-compose exec web python -m pytest -x --ff

coverage: ## Generate coverage report
	docker-compose exec web python -m pytest --cov=apps --cov=chatbot_saas --cov-report=html
	@echo "Coverage report generated in htmlcov/"

lint: ## Run code linting
	docker-compose exec web flake8 apps/ chatbot_saas/
	docker-compose exec web mypy apps/ chatbot_saas/

format: ## Format code with black
	docker-compose exec web black apps/ chatbot_saas/ tests/

format-check: ## Check code formatting
	docker-compose exec web black --check apps/ chatbot_saas/ tests/

security: ## Run security checks
	docker-compose exec web bandit -r apps/ chatbot_saas/
	docker-compose exec web safety check

# Infrastructure and Deployment
deploy-dev: ## Deploy to development environment
	@echo "Deploying to development..."
	terraform -chdir=infrastructure/environments/dev apply -auto-approve

deploy-staging: ## Deploy to staging environment
	@echo "Deploying to staging..."
	terraform -chdir=infrastructure/environments/staging apply -auto-approve

deploy-prod: ## Deploy to production environment
	@echo "Deploying to production..."
	terraform -chdir=infrastructure/environments/prod apply

blue-green-deploy: ## Execute blue-green deployment
	@if [ -z "$(IMAGE_URI)" ]; then \
		echo "Error: IMAGE_URI environment variable is required"; \
		exit 1; \
	fi
	./scripts/blue-green-deploy.sh

# Monitoring and Logging
monitoring-up: ## Start monitoring stack (Prometheus, Grafana)
	docker-compose up -d prometheus grafana

logging-up: ## Start logging stack (ELK)
	docker-compose -f docker-compose.logging.yml up -d

monitoring-down: ## Stop monitoring stack
	docker-compose stop prometheus grafana

logging-down: ## Stop logging stack
	docker-compose -f docker-compose.logging.yml down

health-check: ## Check application health
	@echo "Checking application health..."
	@curl -f http://localhost:8000/health/ || echo "Health check failed"
	@curl -f http://localhost:8000/api/health/ || echo "Detailed health check failed"

# Backup and Restore
backup: ## Create full backup
	./scripts/backup-restore.sh backup

backup-db: ## Backup database only
	docker-compose exec db pg_dump -U postgres chatbot_saas > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore database from backup file
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Usage: make restore-db BACKUP_FILE=backup_file.sql"; \
		exit 1; \
	fi
	docker-compose exec -T db psql -U postgres chatbot_saas < $(BACKUP_FILE)

list-backups: ## List available backups
	./scripts/backup-restore.sh list

# Data Management
load-fixtures: ## Load test data
	docker-compose exec web python manage.py loaddata fixtures/*.json

dump-data: ## Export data to fixtures
	docker-compose exec web python manage.py dumpdata --indent 2 > fixtures/data_$(shell date +%Y%m%d_%H%M%S).json

reset-db: ## Reset database (WARNING: destroys all data)
	docker-compose exec web python manage.py flush --noinput
	docker-compose exec web python manage.py migrate

# Maintenance
clean: ## Clean up Docker resources
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

clean-all: ## Clean up everything (including images)
	docker-compose down -v --remove-orphans
	docker system prune -af
	docker volume prune -f

update-deps: ## Update Python dependencies
	docker-compose exec web pip-compile requirements.in
	docker-compose build web

# Infrastructure Management
infra-init: ## Initialize Terraform
	terraform -chdir=infrastructure init

infra-plan: ## Plan infrastructure changes
	terraform -chdir=infrastructure plan

infra-apply: ## Apply infrastructure changes
	terraform -chdir=infrastructure apply

infra-destroy: ## Destroy infrastructure (USE WITH CAUTION)
	terraform -chdir=infrastructure destroy

# Security and Secrets
setup-secrets: ## Setup AWS Secrets Manager secrets
	@echo "Setting up secrets in AWS Secrets Manager..."
	@aws secretsmanager create-secret --name "chatbot-saas-prod-django-secret-key" --secret-string "$(SECRET_KEY)"
	@aws secretsmanager create-secret --name "chatbot-saas-prod-openai-api-key" --secret-string "$(OPENAI_API_KEY)"

rotate-secrets: ## Rotate application secrets
	@echo "Rotating secrets..."
	@aws secretsmanager rotate-secret --secret-id "chatbot-saas-prod-django-secret-key"

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	docker-compose exec web python manage.py spectacular --file schema.yml
	@echo "API schema generated in schema.yml"

api-docs: ## Open API documentation
	@echo "Opening API documentation..."
	@open http://localhost:8000/api/schema/swagger/ || echo "Open http://localhost:8000/api/schema/swagger/ in your browser"

# CI/CD Helpers
ci-setup: ## Setup for CI environment
	docker-compose -f docker-compose.yml -f docker-compose.ci.yml up -d

ci-test: ## Run tests in CI environment
	docker-compose -f docker-compose.yml -f docker-compose.ci.yml exec -T web python -m pytest --cov=apps --cov=chatbot_saas --cov-report=xml

ci-security: ## Run security checks in CI
	docker-compose -f docker-compose.yml -f docker-compose.ci.yml exec -T web bandit -r apps/ chatbot_saas/ -f json -o bandit-report.json
	docker-compose -f docker-compose.yml -f docker-compose.ci.yml exec -T web safety check --json --output safety-report.json

# Performance and Load Testing
load-test: ## Run load tests
	@echo "Running load tests..."
	@if command -v locust >/dev/null 2>&1; then \
		locust -f tests/load_test.py --host=http://localhost:8000; \
	else \
		echo "Locust not installed. Install with: pip install locust"; \
	fi

benchmark: ## Run performance benchmarks
	docker-compose exec web python manage.py test tests.performance --settings=chatbot_saas.settings.test

# Database Operations
db-backup-prod: ## Backup production database
	@echo "Creating production database backup..."
	@aws rds create-db-snapshot --db-instance-identifier chatbot-saas-prod --db-snapshot-identifier chatbot-saas-prod-$(shell date +%Y%m%d-%H%M%S)

db-restore-prod: ## Restore production database
	@if [ -z "$(SNAPSHOT_ID)" ]; then \
		echo "Usage: make db-restore-prod SNAPSHOT_ID=snapshot-id"; \
		exit 1; \
	fi
	@echo "Restoring production database from snapshot $(SNAPSHOT_ID)..."
	@aws rds restore-db-instance-from-db-snapshot --db-instance-identifier chatbot-saas-prod-restore --db-snapshot-identifier $(SNAPSHOT_ID)

# Utility Commands
check-env: ## Check required environment variables
	@echo "Checking environment variables..."
	@docker-compose config >/dev/null && echo "Environment configuration is valid" || echo "Environment configuration has errors"

ps: ## Show running containers
	docker-compose ps

top: ## Show container resource usage
	docker stats

version: ## Show version information
	@echo "Django RAG Chatbot SaaS"
	@echo "Django version: $(shell docker-compose exec -T web python -c 'import django; print(django.get_version())')"
	@echo "Python version: $(shell docker-compose exec -T web python --version)"
	@echo "Docker version: $(shell docker --version)"
	@echo "Docker Compose version: $(shell docker-compose --version)"