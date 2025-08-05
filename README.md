# CV-Library Scraper

A reliable Python web scraper for CV-Library's recruiter portal that extracts candidate information and downloads CVs automatically.

## 🚀 Features

- **🔐 Automated Authentication**: Seamless login with persistent browser sessions
- **🔍 Smart Search**: Keyword and location-based CV search
- **📥 CV Download**: Automated downloading with detailed candidate extraction
- **📊 Complete Data**: Full contact details, skills, location, and job preferences
- **💾 JSON Export**: Structured data saved as JSON files
- **🛡️ Reliable**: Production-tested with robust error handling

## 📋 Requirements

- Python 3.8+
- Chrome Browser
- Valid CV-Library recruiter account

## 🛠 Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd cv-library-scraper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**
   ```bash
   cp env_example.txt .env
   ```
   Edit `.env` file with your CV-Library login credentials.

## 🎮 Usage

### Quick Start
```bash
# Basic search and download
python production_runner.py --keywords "Python developer" --max-downloads 5

# Search with location
python production_runner.py --keywords "Data Scientist" --location "London" --max-downloads 10

# Multiple keywords
python production_runner.py --keywords "Software Engineer" "Full Stack" --max-downloads 15
```

### Alternative Interface
```bash
# Using the standard runner
python main.py --keywords "Python developer" --quantity 10
```

## 📊 Output

The scraper creates JSON files in `downloaded_cvs/` directory with complete candidate information:

```json
{
  "search_result": {
    "cv_id": "29489739",
    "name": "John Smith",
    "profile_url": "https://www.cv-library.co.uk/...",
    "search_keywords": ["python", "developer"]
  },
  "candidate_info": {
    "name": "John Smith",
    "location": "London, Greater London",
    "personal_job_details": {
      "main_phone": "+447123456789",
      "email": "john.smith@email.com",
      "current_job_title": "Python Developer",
      "expected_salary": "£50,001 - £60,000",
      "job_type": "Permanent"
    },
    "candidates_main_skills": ["Python", "Django", "REST API"],
    "candidates_chosen_industries": ["IT/Internet/Technical"]
  }
}
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file:
```
CV_LIBRARY_EMAIL=your-email@company.com
CV_LIBRARY_PASSWORD=your-password
```

### Settings
- **Headless Mode**: Browser runs invisibly (can be disabled for debugging)
- **Session Persistence**: Maintains login across runs
- **Rate Limiting**: Built-in delays to respect CV-Library's terms
- **Error Recovery**: Automatic retry on failures

## 📁 Project Structure

```
cv-library-scraper/
├── production_runner.py    # Main production interface
├── main.py                 # Alternative interface
├── src/
│   ├── config/             # Configuration files
│   ├── scraper/            # Core scraping logic
│   └── models/             # Data models
├── downloaded_cvs/         # Output directory
├── logs/                   # Log files
└── requirements.txt        # Dependencies
```

## 🔍 Command Line Options

### Production Runner
```bash
python production_runner.py [OPTIONS]

Options:
  --keywords KEYWORDS        Search keywords (required)
  --location LOCATION        Location filter (optional)
  --max-downloads NUMBER     Maximum CVs to download (default: 50)
  --config PATH             Custom config file
```

### Standard Runner
```bash
python main.py [OPTIONS]

Options:
  --keywords KEYWORDS        Search keywords (required)
  --location LOCATION        Location filter (optional)
  --quantity NUMBER          Number of CVs (default: 10)
  --headless true/false      Browser visibility
```

## 📈 Performance

- **Speed**: ~8-10 seconds per candidate
- **Success Rate**: 100% reliability with sequential processing
- **Data Quality**: Complete extraction of all available fields
- **Memory**: Optimized with automatic cleanup

## 🔧 Troubleshooting

### Common Issues

1. **Login Failed**: Check credentials in `.env` file
2. **No CVs Found**: Verify search keywords and location
3. **Browser Issues**: Ensure Chrome is installed and up-to-date

### Debug Mode
```bash
# Run with visible browser for debugging
python main.py --keywords "test" --headless false
```

### Logs
Check `production.log` for detailed execution logs and error information.

## 📜 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

This tool is for legitimate recruitment purposes only. Please ensure compliance with CV-Library's terms of service and applicable data protection regulations.

---

**Ready to start recruiting? Run your first search and download CVs in seconds!** 🚀 