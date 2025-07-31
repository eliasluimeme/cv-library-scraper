# CV-Library Scraper

A robust Python web scraper for CV-Library's recruiter portal that can authenticate, search for CVs using predefined keywords, process results, and download CVs based on specified quantities.

## 🚀 Project Status

**Current Implementation Status: Phase 1-2 Complete (MVP Foundation)**

### ✅ Completed Components

1. **Project Structure & Configuration**
   - Complete directory structure
   - Comprehensive configuration management (YAML + environment variables)
   - Logging system with file rotation
   - Settings validation and error handling

2. **Data Models**
   - CV and candidate information models
   - Search result collections with filtering
   - Data serialization and validation

3. **Utility Framework**
   - Rate limiting and respectful scraping utilities
   - File operations and naming conventions
   - WebDriver utilities and session management
   - Data validation and text processing helpers

4. **CLI Interface**
   - Complete command-line argument parsing
   - Configuration override capabilities
   - Session management and resumption
   - Comprehensive help and validation

### 🚧 In Progress / Next Steps

1. **Authentication System** (Phase 3.1)
   - CV-Library login form detection
   - Session cookie management
   - Login verification and retry logic

2. **Search Functionality** (Phase 3.2)
   - Search form interaction
   - Result parsing and pagination
   - Keyword and location filtering

3. **Download System** (Phase 3.3)
   - CV download queue management
   - File format handling
   - Progress tracking and resume capability

## 📋 Features

### Current Features
- **Configuration Management**: YAML and environment variable configuration
- **Rate Limiting**: Respectful scraping with configurable delays
- **Logging**: Comprehensive logging with file rotation
- **CLI Interface**: Full command-line interface with argument parsing
- **Data Models**: Structured data handling for CVs and search results
- **Session Management**: Save and resume scraping sessions
- **File Utilities**: Safe file operations and naming conventions

### Planned Features
- **Authentication**: Secure login to CV-Library recruiter portal
- **Advanced Search**: Multi-criteria search with pagination
- **Smart Downloads**: Duplicate detection and format preferences
- **Progress Tracking**: Real-time progress bars and statistics
- **Report Generation**: Comprehensive session reports
- **Error Recovery**: Automatic retry and session restoration

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Google Chrome or Firefox browser
- CV-Library recruiter account

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cv-library-scraper
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example environment file
   cp env_example.txt .env
   
   # Edit .env with your credentials
   CV_LIBRARY_USERNAME=your_username
   CV_LIBRARY_PASSWORD=your_password
   ```

5. **Test the installation**
   ```bash
   python main.py --help
   ```

## 📖 Usage

### Basic Usage

```bash
# Search for Python developers in London, download 25 CVs
python main.py --keywords "Python developer" --location "London" --quantity 25

# Use custom configuration file
python main.py --config config/custom_config.yaml

# Resume from previous session
python main.py --resume-session sessions/session_20240101_123456.json

# Dry run to test configuration
python main.py --keywords "Data scientist" --dry-run
```

### Advanced Usage

```bash
# Multiple keywords with salary filtering
python main.py --keywords "DevOps,Docker,Kubernetes" --salary-min 40000 --salary-max 80000

# Custom output directory and file formats
python main.py --keywords "Full stack" --output-dir ./downloads/ --file-formats "pdf,docx"

# Debug mode with custom delays
python main.py --keywords "React" --log-level DEBUG --delay-min 3 --delay-max 7

# Headless browser mode
python main.py --keywords "Machine Learning" --headless true --browser chrome
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# CV-Library Credentials
CV_LIBRARY_USERNAME=your_username
CV_LIBRARY_PASSWORD=your_password

# Download Configuration
DOWNLOAD_PATH=./downloaded_cvs/
MAX_DOWNLOADS_PER_SESSION=50

# Browser Settings
BROWSER=chrome
HEADLESS=true
BROWSER_TIMEOUT=30

# Rate Limiting
DELAY_MIN_SECONDS=2
DELAY_MAX_SECONDS=5
REQUESTS_PER_MINUTE=10
```

### Configuration File (config/config.yaml)
```yaml
search_criteria:
  keywords:
    - "Python developer"
    - "Data scientist"
  locations:
    - "London"
    - "Manchester"
  salary_range:
    min: 30000
    max: 80000

download_settings:
  max_quantity: 100
  file_formats: ["pdf", "doc", "docx"]
  organize_by_keywords: true
```

## 📁 Project Structure

```
cv-library-scraper/
├── src/                          # Source code
│   ├── config/                   # Configuration management
│   │   ├── settings.py          # Settings classes
│   │   └── config_loader.py     # Configuration loader
│   ├── models/                   # Data models
│   │   ├── cv_data.py           # CV and candidate models
│   │   └── search_result.py     # Search result models
│   └── scraper/                  # Core scraping functionality
│       ├── cv_library_scraper.py # Main scraper class
│       ├── auth.py              # Authentication [TODO]
│       ├── search.py            # Search functionality [TODO]
│       ├── download.py          # Download management [TODO]
│       └── utils.py             # Utility functions
├── config/                       # Configuration files
│   ├── config.yaml              # Main configuration
│   └── logging_config.yaml      # Logging configuration
├── downloaded_cvs/               # Downloaded CV files
├── logs/                         # Log files
├── sessions/                     # Session data
├── tests/                        # Test files [TODO]
├── requirements.txt              # Python dependencies
├── main.py                       # CLI entry point
└── README.md                     # Documentation
```

## 🧪 Testing

```bash
# Run basic validation test
python main.py --keywords "test" --dry-run --log-level DEBUG

# Test configuration loading
python -c "from src.config import ConfigLoader; print('Config OK')"

# Test data models
python -c "from src.models import CVData; print('Models OK')"
```

## 📊 Logging

The scraper provides comprehensive logging:

- **Console Output**: Real-time progress and status updates
- **File Logging**: Detailed logs saved to `logs/cv_scraper.log`
- **Error Logging**: Separate error log at `logs/cv_scraper_errors.log`
- **Log Rotation**: Automatic log file rotation (10MB max, 5 backups)

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`

## 🔒 Security & Ethics

### Implemented Safeguards
- **Rate Limiting**: Configurable delays between requests
- **Respectful Scraping**: Honors robots.txt and rate limits
- **Secure Credentials**: Environment variable storage
- **Session Management**: Resumable sessions to avoid re-scraping

### Best Practices
- Always use appropriate delays between requests
- Respect the website's terms of service
- Monitor for anti-bot detection
- Keep credentials secure and never commit them

## 🐛 Troubleshooting

### Common Issues

1. **Configuration Errors**
   ```bash
   # Validate configuration
   python main.py --keywords "test" --dry-run
   ```

2. **Missing Dependencies**
   ```bash
   # Reinstall requirements
   pip install -r requirements.txt --force-reinstall
   ```

3. **WebDriver Issues**
   ```bash
   # Check browser installation
   # Update Chrome/Firefox to latest version
   ```

4. **Permission Errors**
   ```bash
   # Check directory permissions
   chmod 755 downloaded_cvs/ logs/ sessions/
   ```

## 🗺️ Roadmap

### Phase 3: Core Scraping (Next)
- [ ] Authentication system implementation
- [ ] Basic search functionality
- [ ] CV preview parsing
- [ ] Simple download capability

### Phase 4: Enhanced Features
- [ ] Advanced search filters
- [ ] Pagination handling
- [ ] Duplicate detection
- [ ] Progress tracking

### Phase 5: Robustness
- [ ] Error handling and recovery
- [ ] Anti-bot detection
- [ ] Session restoration
- [ ] Comprehensive testing

### Phase 6: Advanced Features
- [ ] GUI interface
- [ ] Database integration
- [ ] Email notifications
- [ ] Scheduling capabilities

## 🤝 Contributing

This project is currently in development. Key areas for contribution:

1. **Core Implementation**: Authentication, search, and download modules
2. **Testing**: Unit and integration tests
3. **Documentation**: API documentation and tutorials
4. **Error Handling**: Robust error recovery mechanisms

## 📄 License

[Add your license information here]

## 📞 Support

For questions and support:
- Check the troubleshooting section
- Review log files for detailed error information
- Ensure all prerequisites are met

---

**Note**: This project is for educational and legitimate recruiting purposes only. Always comply with CV-Library's terms of service and applicable laws. 