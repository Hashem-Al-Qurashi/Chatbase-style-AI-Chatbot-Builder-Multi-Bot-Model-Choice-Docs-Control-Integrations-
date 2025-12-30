# Chatava - Quick Setup Guide

## Prerequisites

1. **Install Docker Desktop**
   - Windows/Mac: https://www.docker.com/products/docker-desktop/
   - Linux: https://docs.docker.com/engine/install/

2. **Get API Keys** (you need these):
   - **OpenAI**: https://platform.openai.com/api-keys
   - **Stripe**: https://dashboard.stripe.com/apikeys
   - **Pinecone**: https://app.pinecone.io/

---

## Quick Start (3 Steps)

### Step 1: Configure Environment

```bash
# Copy the template
cp .env.docker .env

# Edit .env and add your API keys
nano .env   # or use any text editor
```

**Required keys to set:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `STRIPE_SECRET_KEY` - Your Stripe secret key
- `STRIPE_PUBLISHABLE_KEY` - Your Stripe publishable key
- `PINECONE_API_KEY` - Your Pinecone API key

### Step 2: Start the Application

```bash
# On Mac/Linux:
./start.sh

# On Windows (PowerShell):
docker-compose -f docker-compose.simple.yml up --build
```

### Step 3: Access the App

- **Frontend**: http://localhost:3005
- **Backend API**: http://localhost:8000/api/v1/
- **Admin Panel**: http://localhost:8000/admin/

---

## First Time Setup

After starting the app, create an admin user:

```bash
# In a new terminal
docker exec -it chatava_backend python manage.py createsuperuser
```

---

## Common Commands

```bash
# Start the app
./start.sh

# Stop the app
docker-compose -f docker-compose.simple.yml down

# View logs
docker-compose -f docker-compose.simple.yml logs -f

# Restart just the backend
docker-compose -f docker-compose.simple.yml restart backend

# Reset database (WARNING: deletes all data)
docker-compose -f docker-compose.simple.yml down -v
```

---

## Troubleshooting

### "Port already in use"
```bash
# Stop any existing containers
docker-compose -f docker-compose.simple.yml down
# Or change ports in docker-compose.simple.yml
```

### "Database connection refused"
Wait 30 seconds - PostgreSQL takes time to start. Then retry.

### "OpenAI API error"
Check your OPENAI_API_KEY in .env file is correct and has credits.

### Need help?
Contact the developer.
