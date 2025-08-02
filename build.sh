#!/bin/bash

echo "🐳 Building CV-Library Scraper Docker image..."

# Build the Docker image
docker build -t cv-library-scraper:latest .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    echo "📋 Image details:"
    docker images cv-library-scraper:latest
    echo ""
    echo "🚀 To run the scraper:"
    echo "   docker-compose up"
    echo "   or"
    echo "   ./run.sh"
else
    echo "❌ Docker build failed!"
    exit 1
fi 