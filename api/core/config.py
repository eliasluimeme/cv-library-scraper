"""
API Configuration Settings
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    """API configuration settings."""
    
    # Basic API settings
    app_name: str = "CV-Library Scraper API"
    version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security settings
    secret_key: str = Field(default="your-secret-key-change-this-in-production", alias="API_SECRET_KEY")
    api_key_header: str = "X-API-Key"
    access_token_expire_minutes: int = 30
    
    # CORS settings
    allowed_hosts: List[str] = ["*"]
    
    # Database settings
    database_url: Optional[str] = None
    redis_url: str = "redis://localhost:6379/0"
    
    # CV-Library credentials
    cv_library_email: str = Field(alias="CV_LIBRARY_EMAIL")
    cv_library_password: str = Field(alias="CV_LIBRARY_PASSWORD")
    
    # Scraper settings
    max_concurrent_sessions: int = 5
    session_timeout_minutes: int = 60
    max_downloads_per_session: int = Field(default=100, alias="MAX_DOWNLOADS_PER_SESSION")
    
    # Rate limiting
    rate_limit_requests_per_minute: int = Field(default=60, alias="REQUESTS_PER_MINUTE")
    rate_limit_downloads_per_hour: int = 200
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Optional[str] = None
    
    # File storage
    download_base_path: str = Field(default="./api_downloads", alias="DOWNLOAD_PATH")
    temp_file_cleanup_hours: int = 24
    
    @field_validator("allowed_hosts", mode="before")
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False,
        'extra': 'ignore'  # Ignore extra fields from .env file
    }


@lru_cache()
def get_settings() -> APISettings:
    """Get cached application settings."""
    return APISettings() 