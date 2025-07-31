"""
Utility functions for CV-Library Scraper.
Includes rate limiting, file operations, data validation, and helper functions.
"""

import time
import random
import logging
import hashlib
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class RateLimiter:
    """Rate limiting utility for respectful scraping."""
    
    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0, 
                 requests_per_minute: int = 10, exponential_backoff: bool = True):
        """
        Initialize rate limiter.
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            requests_per_minute: Maximum requests per minute
            exponential_backoff: Whether to use exponential backoff on errors
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.requests_per_minute = requests_per_minute
        self.exponential_backoff = exponential_backoff
        self.request_times = []
        self.last_request_time = 0
        self.backoff_multiplier = 1
        self.logger = logging.getLogger(__name__)
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        
        # Clean old request times (older than 1 minute)
        cutoff_time = current_time - 60
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        
        # Check if we've exceeded requests per minute
        if len(self.request_times) >= self.requests_per_minute:
            oldest_request = min(self.request_times)
            wait_time = 60 - (current_time - oldest_request) + 1
            if wait_time > 0:
                self.logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
        
        # Random delay between min and max
        base_delay = random.uniform(self.min_delay, self.max_delay)
        delay = base_delay * self.backoff_multiplier
        
        # Ensure minimum time between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            self.logger.debug(f"Waiting {sleep_time:.1f} seconds before next request")
            time.sleep(sleep_time)
        
        # Record this request
        self.request_times.append(time.time())
        self.last_request_time = time.time()
    
    def on_success(self):
        """Reset backoff multiplier on successful request."""
        self.backoff_multiplier = 1
    
    def on_error(self):
        """Increase backoff multiplier on error."""
        if self.exponential_backoff:
            self.backoff_multiplier = min(self.backoff_multiplier * 2, 8)  # Max 8x delay
            self.logger.debug(f"Error occurred, backoff multiplier increased to {self.backoff_multiplier}")


class FileUtils:
    """File operation utilities."""
    
    @staticmethod
    def create_directory(path: Union[str, Path], exist_ok: bool = True) -> Path:
        """Create directory if it doesn't exist."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=exist_ok)
        return path
    
    @staticmethod
    def generate_unique_filename(base_name: str, extension: str, directory: Union[str, Path]) -> Path:
        """Generate a unique filename by appending numbers if file exists."""
        directory = Path(directory)
        base_path = directory / f"{base_name}.{extension}"
        
        if not base_path.exists():
            return base_path
        
        counter = 1
        while True:
            new_path = directory / f"{base_name}_{counter}.{extension}"
            if not new_path.exists():
                return new_path
            counter += 1
    
    @staticmethod
    def calculate_file_hash(file_path: Union[str, Path], algorithm: str = 'md5') -> str:
        """Calculate hash of a file."""
        file_path = Path(file_path)
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        return Path(file_path).stat().st_size
    
    @staticmethod
    def clean_filename(filename: str, max_length: int = 100) -> str:
        """Clean filename by removing invalid characters."""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)  # Remove control characters
        filename = re.sub(r'\.+$', '', filename)  # Remove trailing dots
        filename = filename.strip()
        
        # Limit length
        if len(filename) > max_length:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = max_length - len(ext) - 1 if ext else max_length
            filename = name[:max_name_length] + ('.' + ext if ext else '')
        
        return filename or 'unnamed_file'


class DataValidator:
    """Data validation utilities."""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def extract_numbers(text: str) -> List[int]:
        """Extract all numbers from text."""
        return [int(match) for match in re.findall(r'\d+', text)]
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text by removing extra whitespace and normalizing."""
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        
        return text


class WebDriverUtils:
    """WebDriver utility functions."""
    
    @staticmethod
    def wait_for_element(driver, by: By, value: str, timeout: int = 10):
        """Wait for element to be present and return it."""
        try:
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            return element
        except TimeoutException:
            return None
    
    @staticmethod
    def wait_for_clickable(driver, by: By, value: str, timeout: int = 10):
        """Wait for element to be clickable and return it."""
        try:
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.element_to_be_clickable((by, value)))
            return element
        except TimeoutException:
            return None
    
    @staticmethod
    def safe_click(driver, element):
        """Safely click an element with retry logic."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Scroll element into view
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Try to click
                element.click()
                return True
                
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(1)
        
        return False
    
    @staticmethod
    def get_text_safe(element) -> str:
        """Safely get text from element."""
        try:
            return DataValidator.clean_text(element.text)
        except Exception:
            return ""
    
    @staticmethod
    def get_attribute_safe(element, attribute: str) -> str:
        """Safely get attribute from element."""
        try:
            value = element.get_attribute(attribute)
            return value if value else ""
        except Exception:
            return ""
    
    @staticmethod
    def find_elements_safe(driver, by: By, value: str) -> List:
        """Safely find elements, return empty list if none found."""
        try:
            return driver.find_elements(by, value)
        except NoSuchElementException:
            return []


class SessionManager:
    """Session persistence utilities."""
    
    def __init__(self, session_path: Union[str, Path]):
        """Initialize session manager."""
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def save_session_data(self, session_id: str, data: Dict[str, Any]):
        """Save session data to file."""
        session_file = self.session_path / f"{session_id}.json"
        
        try:
            # Add timestamp
            data['saved_at'] = datetime.now().isoformat()
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.info(f"Session data saved to {session_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
    
    def load_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from file."""
        session_file = self.session_path / f"{session_id}.json"
        
        if not session_file.exists():
            self.logger.warning(f"Session file {session_file} not found")
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.info(f"Session data loaded from {session_file}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load session data: {e}")
            return None
    
    def generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_part = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
        return f"session_{timestamp}_{random_part}"
    
    def cleanup_old_sessions(self, days_old: int = 7):
        """Remove session files older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for session_file in self.session_path.glob("session_*.json"):
            try:
                file_time = datetime.fromtimestamp(session_file.stat().st_mtime)
                if file_time < cutoff_date:
                    session_file.unlink()
                    self.logger.info(f"Removed old session file: {session_file}")
            except Exception as e:
                self.logger.error(f"Failed to remove old session file {session_file}: {e}")


class ScrapingUtils:
    """Main utility class combining all scraping utilities."""
    
    def __init__(self, settings=None):
        """Initialize scraping utilities with settings."""
        self.settings = settings
        self.rate_limiter = None
        self.session_manager = None
        
        if settings:
            self.rate_limiter = RateLimiter(
                min_delay=settings.scraping.delay_min,
                max_delay=settings.scraping.delay_max,
                requests_per_minute=settings.scraping.requests_per_minute,
                exponential_backoff=settings.scraping.exponential_backoff
            )
            
            self.session_manager = SessionManager(settings.session.session_path)
    
    @staticmethod
    def parse_salary(salary_text: str) -> Dict[str, Optional[int]]:
        """Parse salary information from text."""
        if not salary_text:
            return {'min': None, 'max': None, 'currency': None}
        
        # Remove common currency symbols and words
        clean_text = re.sub(r'[£$€,]', '', salary_text)
        clean_text = re.sub(r'\b(per|annum|year|annual|p\.a\.)\b', '', clean_text, flags=re.IGNORECASE)
        
        # Extract numbers
        numbers = DataValidator.extract_numbers(clean_text)
        
        # Determine currency
        currency = None
        if '£' in salary_text:
            currency = 'GBP'
        elif '$' in salary_text:
            currency = 'USD'
        elif '€' in salary_text:
            currency = 'EUR'
        
        # Parse range or single value
        if len(numbers) >= 2:
            return {
                'min': min(numbers),
                'max': max(numbers), 
                'currency': currency
            }
        elif len(numbers) == 1:
            return {
                'min': numbers[0],
                'max': numbers[0],
                'currency': currency
            }
        else:
            return {'min': None, 'max': None, 'currency': currency}
    
    @staticmethod
    def extract_skills_from_text(text: str) -> List[str]:
        """Extract potential skills from text using common patterns."""
        if not text:
            return []
        
        # Common programming languages and technologies
        tech_skills = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust',
            'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express',
            'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch',
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'Git',
            'Machine Learning', 'AI', 'Data Science', 'Analytics', 'Statistics'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in tech_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to human readable format."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours" 