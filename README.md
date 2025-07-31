# CV-Library Scraper

A robust Python web scraper for CV-Library's recruiter portal that can authenticate, search for CVs using predefined keywords, process results, and download CVs based on specified quantities.

## 🚀 Project Status

**Current Implementation Status: Phase 1-2 COMPLETE ✅ | Phase 3 In Progress 🚧**

### ✅ **COMPLETED FEATURES (Phase 1-2)**

#### 1. **Project Structure & Configuration** ✅
- ✅ Complete directory structure with proper Python packages
- ✅ Comprehensive configuration management (YAML + environment variables)
- ✅ Logging system with file rotation and multiple handlers
- ✅ Settings validation and error handling
- ✅ Environment variable management with .env support

#### 2. **Data Models** ✅
- ✅ CV and candidate information models with full serialization
- ✅ Search result collections with filtering and sorting capabilities
- ✅ Data validation and type safety with dataclasses
- ✅ Duplicate detection algorithms
- ✅ File naming conventions and metadata tracking

#### 3. **Utility Framework** ✅
- ✅ Rate limiting and respectful scraping utilities
- ✅ File operations and safe filename generation
- ✅ WebDriver utilities with retry logic
- ✅ Session management and persistence
- ✅ Data validation and text processing helpers
- ✅ Progress tracking and statistics utilities

#### 4. **CLI Interface** ✅
- ✅ Complete command-line interface with comprehensive options
- ✅ Configuration override capabilities
- ✅ Session management and resumption
- ✅ Dry-run mode for testing
- ✅ Multiple output formats and logging levels
- ✅ Comprehensive help and validation

#### 5. **Core Architecture** ✅
- ✅ Main `CVLibraryScraper` class with workflow coordination
- ✅ Modular architecture with separate managers for auth/search/download
- ✅ Session tracking and persistence (JSON-based)
- ✅ Comprehensive error handling and logging
- ✅ Resource cleanup and graceful shutdown

### 🚧 **IN PROGRESS (Phase 3)**

#### Authentication System 🔄
- 🚧 CV-Library login form detection and interaction
- 🚧 Session cookie management and persistence
- 🚧 Login verification and retry logic

#### Search Functionality 🔄
- 🚧 Search form interaction with CV-Library portal
- 🚧 Result parsing and pagination handling
- 🚧 Advanced filtering and keyword matching

#### Download System 🔄
- 🚧 CV download queue management
- 🚧 File format handling and organization
- 🚧 Progress tracking and resume capability

## 📋 Current Working Features

### **Configuration Management**
- YAML and environment variable configuration ✅
- Multi-source configuration loading ✅
- Configuration validation and error reporting ✅

### **Logging System**
- Comprehensive logging with file rotation ✅
- Multiple log levels and handlers ✅
- Separate error logging ✅

### **Session Management**
- Save and resume scraping sessions ✅
- Session data persistence in JSON format ✅
- Automatic session ID generation ✅

### **CLI Interface**
- Full command-line interface with argument parsing ✅
- Configuration override capabilities ✅
- Dry-run mode for testing configurations ✅

### **Data Handling**
- Structured data models for CVs and search results ✅
- Data serialization and validation ✅
- File utilities and naming conventions ✅

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher (tested with Python 3.13)
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

### **Working Commands (Phase 1-2)**

#### Basic Testing
```bash
# Test configuration and CLI
python main.py --help

# Dry run to test configuration
python main.py --keywords "Python developer" --location "London" --dry-run

# Test with configuration file
python main.py --config config/config.yaml --dry-run
```

#### Session Management
```bash
# Run with session saving
python main.py --keywords "Data scientist" --save-session

# Resume from saved session (when Phase 3 is complete)
python main.py --resume-session sessions/session_20250731_180307_20jcvs.json
```

#### Advanced Configuration
```bash
# Custom output directory and file formats
python main.py --keywords "DevOps" --output-dir ./downloads/ --file-formats "pdf,docx"

# Debug mode with custom delays
python main.py --keywords "React" --log-level DEBUG --delay-min 3 --delay-max 7

# Different browser settings
python main.py --keywords "Machine Learning" --headless false --browser chrome
```

### **Example Output**

```bash
$ python main.py --keywords "Python developer" --location "London" --quantity 5 --dry-run

╔═══════════════════════════════════════════════════════════════╗
║                    CV-Library Scraper v1.0                   ║
║         Automated CV downloading from CV-Library portal       ║
╚═══════════════════════════════════════════════════════════════╝

📋 Configuration Summary:
   Search Keywords: Python developer
   Search Locations: London
   Download Quantity: 5
   Download Path: ./downloaded_cvs/
   Browser: chrome (headless: True)
   Rate Limiting: 2-5s delays

🚀 CV-Library Scraper initialized successfully!
   🔍 Dry run mode - no actual scraping will be performed

✅ All systems ready! The scraper would now:
   1. 🔐 Authenticate with CV-Library
   2. 🔍 Search for CVs matching criteria
   3. 📄 Parse and filter results
   4. ⬇️  Download selected CVs
   5. 📊 Generate reports
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

## 📁 Current Project Structure

```
cv-library-scraper/
├── src/                          # Source code ✅
│   ├── __init__.py              # Package initialization ✅
│   ├── config/                   # Configuration management ✅
│   │   ├── __init__.py          # Config package ✅
│   │   ├── settings.py          # Settings classes ✅
│   │   └── config_loader.py     # Configuration loader ✅
│   ├── models/                   # Data models ✅
│   │   ├── __init__.py          # Models package ✅
│   │   ├── cv_data.py           # CV and candidate models ✅
│   │   └── search_result.py     # Search result models ✅
│   └── scraper/                  # Core scraping functionality ✅
│       ├── __init__.py          # Scraper package ✅
│       ├── cv_library_scraper.py # Main scraper class ✅
│       ├── auth.py              # Authentication [Phase 3] 🚧
│       ├── search.py            # Search functionality [Phase 3] 🚧
│       ├── download.py          # Download management [Phase 3] 🚧
│       └── utils.py             # Utility functions ✅
├── config/                       # Configuration files ✅
│   ├── config.yaml              # Main configuration ✅
│   └── logging_config.yaml      # Logging configuration ✅
├── downloaded_cvs/               # Downloaded CV files ✅
├── logs/                         # Log files ✅
│   ├── cv_scraper.log           # Main log file ✅
│   └── cv_scraper_errors.log    # Error log file ✅
├── sessions/                     # Session data ✅
│   └── session_*.json           # Saved session files ✅
├── tests/                        # Test files [Future]
├── requirements.txt              # Python dependencies ✅
├── main.py                       # CLI entry point ✅
├── env_example.txt              # Environment template ✅
└── README.md                     # Documentation ✅
```

## 🧪 Testing Current Features

```bash
# Test configuration loading
python -c "from src.config import ConfigLoader; print('✅ Config loading works')"

# Test data models
python -c "from src.models import CVData; print('✅ Data models work')"

# Test CLI with different options
python main.py --keywords "test" --dry-run --log-level DEBUG

# Test session management
python main.py --keywords "Python" --save-session
ls sessions/  # Check for saved session file
```

## 📊 Logging

The scraper provides comprehensive logging:

- **Console Output**: Real-time progress and status updates ✅
- **File Logging**: Detailed logs saved to `logs/cv_scraper.log` ✅
- **Error Logging**: Separate error log at `logs/cv_scraper_errors.log` ✅
- **Log Rotation**: Automatic log file rotation (10MB max, 5 backups) ✅

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`

## 🔒 Security & Ethics

### Implemented Safeguards ✅
- **Rate Limiting**: Configurable delays between requests
- **Respectful Scraping**: Built-in robots.txt compliance
- **Secure Credentials**: Environment variable storage
- **Session Management**: Resumable sessions to avoid re-scraping

## 🗺️ Development Roadmap

### ✅ **Phase 1-2: Foundation (COMPLETE)**
- [x] Project structure and configuration management
- [x] Data models and utilities
- [x] CLI interface and session management
- [x] Logging and error handling
- [x] Rate limiting and ethical scraping framework

### 🚧 **Phase 3: Core Scraping (IN PROGRESS)**
- [ ] Authentication system implementation
- [ ] Basic search functionality
- [ ] CV preview parsing
- [ ] Simple download capability

### 📋 **Phase 4: Enhanced Features (PLANNED)**
- [ ] Advanced search filters
- [ ] Pagination handling
- [ ] Duplicate detection
- [ ] Progress tracking

### 🔮 **Phase 5: Advanced Features (FUTURE)**
- [ ] GUI interface
- [ ] Database integration
- [ ] Email notifications
- [ ] Scheduling capabilities

## 🎯 **Current Implementation Status**

- **Foundation**: 100% Complete ✅
- **Configuration**: 100% Complete ✅  
- **CLI Interface**: 100% Complete ✅
- **Data Models**: 100% Complete ✅
- **Session Management**: 100% Complete ✅
- **Authentication**: 0% (Phase 3 Next) 🚧
- **Search**: 0% (Phase 3 Next) 🚧
- **Download**: 0% (Phase 3 Next) 🚧

---

**Ready for Phase 3!** The foundation is solid and all core infrastructure is in place. Next step: Implement CV-Library authentication, search, and download functionality. 