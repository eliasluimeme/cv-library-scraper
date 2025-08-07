# CV-Library Scraper API

A FastAPI-based REST API for the CV-Library scraper, providing scalable and concurrent access to CV scraping functionality with a unified search and download workflow.

## 🚀 Features

- **RESTful API**: Clean, documented endpoints following REST conventions
- **Unified Workflow**: Single operation that searches and downloads CVs automatically
- **Async Operations**: Non-blocking operations with real-time progress tracking
- **Session Management**: Persistent browser sessions with automatic cleanup
- **Concurrent Processing**: Handle multiple scraping sessions simultaneously
- **Real-time Status**: Track progress of scraping operations
- **Comprehensive Monitoring**: Health checks, metrics, and logging
- **Docker Support**: Containerized deployment ready
- **OpenAPI Documentation**: Auto-generated API docs with Swagger UI

## 📋 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Authenticate with CV-Library
- `GET /api/v1/auth/status/{session_id}` - Check authentication status
- `DELETE /api/v1/auth/logout/{session_id}` - Logout and cleanup

### Scraping (Search + Download)
- `POST /api/v1/scrape` - Initiate complete CV scraping operation
- `GET /api/v1/scrape/{scrape_id}` - Get scraping status and results
- `GET /api/v1/scrape/session/{session_id}/list` - List scrapes for a session

### Sessions
- `GET /api/v1/sessions` - List active sessions
- `GET /api/v1/sessions/{session_id}` - Get session details
- `DELETE /api/v1/sessions/{session_id}` - Clean up session

### Health & Monitoring
- `GET /api/v1/health` - Comprehensive health check
- `GET /api/v1/health/simple` - Simple health check
- `GET /api/v1/health/ready` - Readiness check
- `GET /api/v1/health/live` - Liveness check

## 🛠 Installation & Setup

### Prerequisites
- Python 3.11+
- Chrome Browser (for Docker: included in image)
- CV-Library recruiter account credentials

### Local Development

1. **Clone and setup**
   ```bash
   git clone <your-repo-url>
   cd cv-library-scraper
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp env_example.txt .env
   # Edit .env with your credentials and API settings
   ```

3. **Start the API**
   ```bash
   python start_api.py
   ```

4. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Build the API image**
   ```bash
   docker build -f Dockerfile.api -t cv-scraper-api .
   ```

2. **Run with environment variables**
   ```bash
   docker run -p 8000:8000 \
     -e CV_LIBRARY_EMAIL="your-email@domain.com" \
     -e CV_LIBRARY_PASSWORD="your-password" \
     -e API_SECRET_KEY="your-secret-key" \
     cv-scraper-api
   ```

3. **Or use docker-compose** (create docker-compose.api.yml)
   ```yaml
   version: '3.8'
   services:
     cv-scraper-api:
       build:
         context: .
         dockerfile: Dockerfile.api
       ports:
         - "8000:8000"
       environment:
         - CV_LIBRARY_EMAIL=${CV_LIBRARY_EMAIL}
         - CV_LIBRARY_PASSWORD=${CV_LIBRARY_PASSWORD}
         - API_SECRET_KEY=${API_SECRET_KEY}
       volumes:
         - ./api_downloads:/app/api_downloads
         - ./logs:/app/logs
       restart: unless-stopped
   ```

## ⚙️ Configuration

### Environment Variables

```bash
# Required
CV_LIBRARY_EMAIL=your-email@domain.com
CV_LIBRARY_PASSWORD=your-password

# API Settings
API_SECRET_KEY=your-secret-key-change-in-production
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Scraper Settings
MAX_CONCURRENT_SESSIONS=5
SESSION_TIMEOUT_MINUTES=60
MAX_DOWNLOADS_PER_SESSION=100

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_DOWNLOADS_PER_HOUR=200

# Storage
DOWNLOAD_BASE_PATH=./api_downloads
TEMP_FILE_CLEANUP_HOURS=24

# Optional: Database & Cache
DATABASE_URL=postgresql://user:pass@localhost:5432/cvscraperdb
REDIS_URL=redis://localhost:6379/0
```

## 🎮 Usage Examples

### 1. Authentication

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-email@domain.com",
    "password": "your-password",
    "remember_session": true
  }'
```

Response:
```json
{
  "success": true,
  "message": "Authentication successful",
  "timestamp": "2024-01-15T10:30:00Z",
  "session_id": "uuid-session-id",
  "status": "authenticated",
  "expires_at": "2024-01-15T11:30:00Z"
}
```

### 2. Start Scraping Operation (Search + Download) - Production-Ready Filters

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-session-id",
    "keywords": ["Senior Software Engineer", "Python"],
    "location": "London", 
    "max_downloads": 10,
    
    // Salary filters
    "salary_min": "50000",
    "salary_max": "80000",
    
    // Job and industry filters
    "job_type": ["Permanent", "Contract"],
    "industry": ["IT/Internet/Technical"],
    
    // Location and timing filters
    "distance": 25,
    "time_period": "7",
    
    // Boolean filters
    "willing_to_relocate": false,
    "uk_driving_licence": true,
    "hide_recently_viewed": true,
    
    // Advanced filters
    "languages": ["French"],
    "minimum_match": "60",
    "sort_order": "relevancy desc",
    
    // Advanced keyword filters
    "must_have_keywords": "Python Django",
    "any_keywords": "AWS Azure GCP",
    "none_keywords": "junior intern",
    
    // Download options
    "file_formats": ["pdf", "docx"],
    "organize_by_keywords": false
  }'
```

**Key Features:**
- 🎯 **Smart Pagination**: Only crawls pages needed for target quantity
- 🔍 **Comprehensive Filtering**: Full production CLI feature set
- 📊 **Real-time Progress**: Track search and download phases  
- 🚀 **Optimized Performance**: Same logic as production runner

### 3. Monitor Scraping Progress

```bash
curl "http://localhost:8000/api/v1/scrape/scrape_uuid"
```

**During Operation Response:**
```json
{
  "success": true,
  "message": "Scrape operation running",
  "timestamp": "2024-01-15T10:32:00Z",
  "scrape_id": "scrape_uuid",
  "session_id": "uuid-session-id",
  "status": "running",
  "keywords_used": ["Python", "Django", "REST API"],
  "location_used": "London",
  "progress": {
    "phase": "downloading",
    "total_candidates_found": 25,
    "total_to_download": 10,
    "downloaded": 7,
    "failed": 0,
    "current_operation": "Downloading CV for John Smith",
    "percentage": 70.0,
    "estimated_time_remaining": 45
  }
}
```

**Completed Operation Response:**
```json
{
  "success": true,
  "message": "Scrape operation completed",
  "timestamp": "2024-01-15T10:35:00Z",
  "scrape_id": "scrape_uuid",
  "session_id": "uuid-session-id",
  "status": "completed",
  "total_found": 25,
  "keywords_used": ["Python", "Django", "REST API"],
  "location_used": "London",
  "progress": {
    "phase": "completed",
    "total_candidates_found": 25,
    "total_to_download": 10,
    "downloaded": 10,
    "failed": 0,
    "percentage": 100.0
  },
  "downloaded_files": [
    {
      "file_id": "file_1",
      "candidate_name": "John Smith",
      "filename": "john_smith_cv.pdf",
      "file_path": "./api_downloads/john_smith_cv.pdf",
      "file_size": 245760,
      "file_format": "pdf",
      "download_timestamp": "2024-01-15T10:33:00Z"
    }
  ],
  "operation_duration": 180.5,
  "stats": {
    "total_candidates_found": 25,
    "total_downloaded": 10,
    "success_rate": 40.0
  }
}
```

### 4. List Session Scrapes

```bash
curl "http://localhost:8000/api/v1/scrape/session/uuid-session-id/list"
```

Response:
```json
{
  "success": true,
  "message": "Scrape operations retrieved",
  "session_id": "uuid-session-id",
  "scrapes": [
    {
      "scrape_id": "scrape_uuid",
      "status": "completed",
      "keywords": ["Python", "Django", "REST API"],
      "location": "London",
      "progress": {
        "phase": "completed",
        "percentage": 100.0
      },
      "start_time": 1705320660,
      "duration": 180.5
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

## 📊 API Response Structure

All API responses follow a consistent structure:

### Success Response
```json
{
  "success": true,
  "message": "Operation description",
  "timestamp": "2024-01-15T10:30:00Z",
  // ... endpoint-specific data
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error description",
  "timestamp": "2024-01-15T10:30:00Z",
  "error_code": "AUTH_FAILED",
  "details": {
    "field": "validation error details"
  }
}
```

## 🔧 Architecture

### Unified Workflow

The API now follows the same pattern as the original CLI script:

1. **Authentication** - Login to CV-Library once per session
2. **Scraping** - Single operation that searches AND downloads CVs
3. **Progress Tracking** - Real-time updates on search and download progress
4. **Results** - Complete information about found candidates and downloaded files

### Components

1. **FastAPI Application** (`api/main.py`)
   - Main application setup
   - Middleware configuration
   - Route registration

2. **Routers** (`api/routers/`)
   - Authentication endpoints
   - Scraping endpoints (combined search + download)
   - Session management
   - Health checks

3. **Services** (`api/services/`)
   - `SessionManager`: Browser session lifecycle
   - `ScraperService`: Integration with existing scraper
   - `TaskManager`: Background task handling

4. **Models** (`api/models/`)
   - Request/response Pydantic models
   - Data validation schemas

5. **Core** (`api/core/`)
   - Configuration management
   - Logging setup
   - Security utilities

### Session Management

The API maintains browser sessions for authenticated users:
- Each login creates a unique session ID
- Sessions persist browser state (cookies, authentication)
- Automatic cleanup of expired sessions
- Support for concurrent sessions (configurable limit)

### Background Tasks

Scraping operations run as background tasks:
- Non-blocking API responses
- Real-time progress tracking through phases:
  - `pending` → `searching` → `downloading` → `completed`
- Automatic cleanup on completion
- Error handling and recovery

## 🔒 Security

- **Authentication**: CV-Library credentials required
- **Session Management**: Secure session tokens
- **Rate Limiting**: Configurable request limits
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Secure error responses
- **Docker Security**: Non-root user execution

## 📈 Monitoring & Logging

### Health Checks
- `/health` - Comprehensive system status
- `/health/ready` - Kubernetes readiness probe
- `/health/live` - Kubernetes liveness probe

### Metrics
- Active sessions count
- Active scraping operations
- Request/response times
- Success/failure rates
- Resource usage (CPU, memory, disk)

### Logging
- Structured JSON logging
- Request/response logging
- Scraping operation progress
- Error tracking with stack traces
- Configurable log levels

## 🚀 Deployment

The deployment configuration remains the same as described in the original documentation. The unified workflow actually simplifies deployment since there are fewer moving parts.

## 📝 Development

### Workflow Comparison

**Original CLI:**
```bash
python production_runner.py --keywords "Python developer" --max-downloads 10
```

**New API:**
```bash
# 1. Login
session_id=$(curl -X POST /api/v1/auth/login -d '{"username":"user","password":"pass"}' | jq -r .session_id)

# 2. Scrape (search + download)
scrape_id=$(curl -X POST /api/v1/scrape -d "{\"session_id\":\"$session_id\",\"keywords\":[\"Python developer\"],\"max_downloads\":10}" | jq -r .scrape_id)

# 3. Monitor progress
curl /api/v1/scrape/$scrape_id
```

## 🤝 Migration Benefits

The unified API approach provides:
- **Simplified Usage**: One operation instead of separate search/download steps
- **Better Progress Tracking**: Real-time updates through all phases
- **Consistent with CLI**: Same workflow as the original script
- **Reduced Complexity**: Fewer endpoints to manage
- **Improved Reliability**: Atomic operations reduce failure points

## 📚 API Documentation

Once the API is running, comprehensive documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔄 Best Practices

1. **Always authenticate first** before starting scraping operations
2. **Monitor scrape progress** to track operation status
3. **Use appropriate timeouts** for long-running operations
4. **Implement retries** for transient failures
5. **Clean up sessions** when no longer needed
6. **Respect rate limits** to maintain service stability
7. **Check progress regularly** during scraping operations

---

For questions or issues, please refer to the main README.md or create an issue in the repository. 