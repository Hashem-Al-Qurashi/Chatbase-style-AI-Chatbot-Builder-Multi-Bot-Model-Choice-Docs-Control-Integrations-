@echo off
echo ========================================
echo    Starting Chatava
echo ========================================

REM Set environment for SQLite local dev
set DATABASE_URL=sqlite:///db.sqlite3
set CELERY_TASK_ALWAYS_EAGER=True
set CELERY_TASK_EAGER_PROPAGATES=True
set DEBUG=True
set ENVIRONMENT=development
set SECRET_KEY=local-dev-secret-key-not-for-production
set REDIS_URL=
set ENABLE_CACHING=False
set ENABLE_RATE_LIMITING=False

REM OpenAI - Required for chatbot
set OPENAI_API_KEY=your-openai-api-key-here

REM Stripe - Required for billing
set STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key-here
set STRIPE_SECRET_KEY=your-stripe-secret-key-here
set STRIPE_WEBHOOK_SECRET=whsec_placeholder

REM JWT
set JWT_SECRET_KEY=local-jwt-secret-key

REM Disabled features
set PINECONE_API_KEY=
set AWS_ACCESS_KEY_ID=
set AWS_SECRET_ACCESS_KEY=

echo.
echo Starting Backend on http://localhost:8000
echo Starting Frontend on http://localhost:3005
echo.
echo Press Ctrl+C in each window to stop
echo.

REM Start backend in new window
start "Chatava Backend" cmd /k "call venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
start "Chatava Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo ========================================
echo    App is starting...
echo ========================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3005
echo.
echo Two windows opened - one for backend, one for frontend.
echo.
pause
