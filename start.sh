#!/bin/bash

# Chatava - Simple Startup Script
# ================================

echo "🚀 Starting Chatava..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Creating .env from template..."
    cp .env.docker .env
    echo ""
    echo "⚠️  IMPORTANT: Edit the .env file with your API keys before running again:"
    echo "   - OPENAI_API_KEY (required)"
    echo "   - STRIPE_SECRET_KEY (required for billing)"
    echo "   - STRIPE_PUBLISHABLE_KEY (required for billing)"
    echo "   - PINECONE_API_KEY (required for vector search)"
    echo ""
    echo "Run this script again after editing .env"
    exit 1
fi

# Check if required env vars are set
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-api-key-here" ]; then
    echo "❌ OPENAI_API_KEY is not set in .env file"
    exit 1
fi

echo "✅ Configuration looks good!"
echo ""
echo "🐳 Starting Docker containers..."
echo ""

# Use docker compose (v2) or docker-compose (v1)
if docker compose version &> /dev/null; then
    docker compose -f docker-compose.simple.yml up --build
else
    docker-compose -f docker-compose.simple.yml up --build
fi
