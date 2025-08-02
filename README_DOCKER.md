# CV-Library Scraper - Docker Setup 🐳

This document provides instructions for running the CV-Library Scraper in a Docker container, which eliminates all ChromeDriver and environment setup issues.

## 🚀 Quick Start

### Prerequisites
- Docker installed on your system
- Docker Compose (optional, but recommended)
- Your CV-Library credentials

### 1. Setup Environment Variables
```bash
# Copy the example environment file
cp env_example.txt .env

# Edit .env with your credentials
nano .env
```

Add your CV-Library credentials:
```
CV_LIBRARY_USERNAME=your_username
CV_LIBRARY_PASSWORD=your_password
```

### 2. Build and Run (Easy Way)
```bash
# Make scripts executable (if not already)
chmod +x build.sh run.sh

# Build the Docker image
./build.sh

# Run the scraper
./run.sh --keywords "Python developer" --quantity 5
```

### 3. Alternative: Using Docker Compose
```bash
# Run with docker-compose
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f
```

## 📋 Usage Examples

### Basic Usage
```bash
# Search for Python developers, download 5 CVs
./run.sh --keywords "Python developer" --quantity 5

# Search for Java developers in London, download 10 CVs
./run.sh --keywords "Java developer" --location "London" --quantity 10

# Search for DevOps engineers, download 3 CVs
./run.sh --keywords "DevOps engineer" --quantity 3
```

### Advanced Usage
```bash
# Run in non-headless mode (for debugging)
./run.sh --keywords "React developer" --headless false --quantity 2

# Interactive mode for debugging
./run.sh --interactive

# Get help
./run.sh --help
```

## 🛠️ Docker Commands

### Building the Image
```bash
# Build the image manually
docker build -t cv-library-scraper:latest .

# Build with no cache (force rebuild)
docker build --no-cache -t cv-library-scraper:latest .
```

### Running the Container
```bash
# Basic run
docker run --rm \
  -v "$(pwd)/downloaded_cvs:/app/downloaded_cvs" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/.env:/app/.env:ro" \
  cv-library-scraper:latest --keywords "Python developer" --quantity 5

# Interactive mode for debugging
docker run -it --rm \
  -v "$(pwd)/downloaded_cvs:/app/downloaded_cvs" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/.env:/app/.env:ro" \
  cv-library-scraper:latest bash
```

### Managing Containers
```bash
# List running containers
docker ps

# Stop a running container
docker stop cv-library-scraper

# Remove stopped containers
docker container prune

# View container logs
docker logs cv-library-scraper
```

## 📁 Directory Structure

The Docker setup uses volume mounts to persist data:

```
cv-library-scraper/
├── downloaded_cvs/     # Downloaded CV files (mounted)
├── logs/              # Application logs (mounted)
├── sessions/          # Browser session data (mounted)
├── config/            # Configuration files (mounted)
├── .env              # Environment variables (mounted read-only)
├── Dockerfile        # Docker image definition
├── docker-compose.yml # Docker Compose configuration
├── build.sh          # Build script
├── run.sh            # Run script
└── README_DOCKER.md  # This file
```

## 🔧 Configuration

### Environment Variables
- `CV_LIBRARY_USERNAME`: Your CV-Library username
- `CV_LIBRARY_PASSWORD`: Your CV-Library password
- `HEADLESS`: Run browser in headless mode (default: true)

### Docker Environment
The container includes:
- Python 3.11
- Google Chrome (latest stable)
- ChromeDriver (matching Chrome version)
- All Python dependencies
- Virtual display support (Xvfb)

## 🐛 Troubleshooting

### Common Issues

#### 1. Permission Denied
```bash
# Make scripts executable
chmod +x build.sh run.sh

# Check Docker permissions
sudo docker ps
```

#### 2. .env File Not Found
```bash
# Create .env file
cp env_example.txt .env
# Edit with your credentials
nano .env
```

#### 3. Chrome/ChromeDriver Issues
The Docker container handles all Chrome/ChromeDriver setup automatically. If you encounter issues:

```bash
# Rebuild the image
docker build --no-cache -t cv-library-scraper:latest .

# Check Chrome version in container
docker run --rm cv-library-scraper:latest google-chrome --version
docker run --rm cv-library-scraper:latest chromedriver --version
```

#### 4. Memory Issues
```bash
# Increase Docker memory limit (Docker Desktop)
# Settings > Resources > Advanced > Memory

# Or run with memory limit
docker run --rm --memory="4g" cv-library-scraper:latest
```

#### 5. Network Issues
```bash
# Check if container can reach CV-Library
docker run --rm cv-library-scraper:latest ping cv-library.co.uk

# Run with host network (debugging)
docker run --rm --network host cv-library-scraper:latest
```

### Debug Mode

For debugging, use interactive mode:
```bash
./run.sh --interactive

# Inside the container:
root@container:/app# python main.py --keywords "test" --quantity 1 --headless false
root@container:/app# google-chrome --version
root@container:/app# chromedriver --version
```

## 📊 Performance

### Image Size
- Base image: ~400MB
- Final image: ~800MB (includes Chrome + dependencies)

### Build Time
- First build: 3-5 minutes
- Subsequent builds: 30 seconds (with cache)

### Runtime Performance
- Startup time: 5-10 seconds
- Search performance: Same as native (no overhead)
- Memory usage: ~500MB-1GB

## 🔄 Updates

### Updating the Application
```bash
# Pull latest code changes
git pull

# Rebuild the image
./build.sh

# Run updated version
./run.sh
```

### Updating Chrome/ChromeDriver
Chrome and ChromeDriver are automatically updated during image build:
```bash
# Force rebuild to get latest Chrome
docker build --no-cache -t cv-library-scraper:latest .
```

## 📝 Tips

1. **Use volume mounts** to persist data between container runs
2. **Run in headless mode** for better performance in production
3. **Use interactive mode** for debugging and development
4. **Monitor logs** in `logs/` directory for troubleshooting
5. **Keep .env secure** - don't commit credentials to git

## 🆘 Support

If you encounter issues:

1. Check the logs in `logs/cv_scraper.log`
2. Try running in interactive mode: `./run.sh --interactive`
3. Rebuild the image: `docker build --no-cache -t cv-library-scraper:latest .`
4. Check Docker system: `docker system info`

## 🎯 Next Steps

- Set up automated runs with cron
- Integrate with CI/CD pipeline
- Deploy to cloud containers (AWS ECS, GCP Cloud Run, etc.)
- Add monitoring and alerting 