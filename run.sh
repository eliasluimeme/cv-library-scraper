#!/bin/bash

# Default values
KEYWORDS="Python developer"
QUANTITY=5
HEADLESS=true
LOCATION=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --keywords)
            KEYWORDS="$2"
            shift 2
            ;;
        --quantity)
            QUANTITY="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --headless)
            HEADLESS="$2"
            shift 2
            ;;
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --keywords KEYWORDS    Search keywords (default: 'Python developer')"
            echo "  --quantity NUMBER      Number of CVs to download (default: 5)"
            echo "  --location LOCATION    Search location (optional)"
            echo "  --headless true/false  Run in headless mode (default: true)"
            echo "  --interactive          Run in interactive mode for debugging"
            echo "  --help                 Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --keywords 'Java developer' --quantity 10"
            echo "  $0 --keywords 'DevOps engineer' --location 'London' --quantity 3"
            echo "  $0 --interactive  # For debugging"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Create .env file with your CV-Library credentials:"
    echo ""
    echo "CV_LIBRARY_USERNAME=your_username"
    echo "CV_LIBRARY_PASSWORD=your_password"
    echo ""
    echo "You can also copy from env_example.txt:"
    echo "cp env_example.txt .env"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "🐳 Running CV-Library Scraper in Docker..."
echo "📋 Configuration:"
echo "   Keywords: $KEYWORDS"
echo "   Quantity: $QUANTITY"
echo "   Location: $LOCATION"
echo "   Headless: $HEADLESS"
echo ""

# Build command arguments
CMD_ARGS=("--keywords" "$KEYWORDS" "--quantity" "$QUANTITY" "--headless" "$HEADLESS")

if [ -n "$LOCATION" ]; then
    CMD_ARGS+=("--location" "$LOCATION")
fi

# Check if image exists
if [[ "$(docker images -q cv-library-scraper:latest 2> /dev/null)" == "" ]]; then
    echo "📦 Docker image not found. Building..."
    ./build.sh
    if [ $? -ne 0 ]; then
        echo "❌ Failed to build Docker image"
        exit 1
    fi
fi

# Create directories if they don't exist
mkdir -p downloaded_cvs logs sessions

# Run the container
if [ "$INTERACTIVE" = "true" ]; then
    echo "🔧 Running in interactive mode for debugging..."
    docker run -it --rm \
        --name cv-library-scraper-debug \
        -v "$(pwd)/downloaded_cvs:/app/downloaded_cvs" \
        -v "$(pwd)/logs:/app/logs" \
        -v "$(pwd)/sessions:/app/sessions" \
        -v "$(pwd)/.env:/app/.env:ro" \
        -v "$(pwd)/config:/app/config" \
        -e HEADLESS=$HEADLESS \
        cv-library-scraper:latest bash
else
    echo "🚀 Starting scraper..."
    docker run --rm \
        --name cv-library-scraper \
        -v "$(pwd)/downloaded_cvs:/app/downloaded_cvs" \
        -v "$(pwd)/logs:/app/logs" \
        -v "$(pwd)/sessions:/app/sessions" \
        -v "$(pwd)/.env:/app/.env:ro" \
        -v "$(pwd)/config:/app/config" \
        -e HEADLESS=$HEADLESS \
        cv-library-scraper:latest "${CMD_ARGS[@]}"
fi 