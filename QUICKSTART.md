# Chatava - Quick Start (2 Minutes)

## Step 1: Install Docker
Download and install Docker Desktop:
- **Windows/Mac**: https://www.docker.com/products/docker-desktop/
- **Linux**: https://docs.docker.com/engine/install/

## Step 2: Run the App

```bash
# Clone the project
git clone https://github.com/ismahiltcha/chatava.git
cd chatava

# Start everything (first time takes ~3 minutes to build)
docker-compose -f docker-compose.production.yml up --build
```

## Step 3: Open the App

- **App**: http://localhost:3005
- **API**: http://localhost:8000

## That's it!

---

## Common Commands

```bash
# Stop the app
docker-compose -f docker-compose.production.yml down

# Start again (faster after first build)
docker-compose -f docker-compose.production.yml up

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Reset everything (deletes database)
docker-compose -f docker-compose.production.yml down -v
```

## Create Admin User

```bash
docker exec -it chatava_backend python manage.py createsuperuser
```

Then login at: http://localhost:8000/admin
