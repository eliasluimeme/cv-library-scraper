"""
Response models for the CV-Library Scraper API with production-level reporting
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProductionMetrics(BaseModel):
    """Production-level performance metrics."""
    avg_time_per_operation: str = Field(..., description="Average time per operation")
    total_operations: int = Field(default=0, description="Total operations performed")
    success_rate: float = Field(default=100.0, description="Success rate percentage")


class ProductionConfig(BaseModel):
    """Production environment configuration info."""
    headless_mode: bool = Field(..., description="Whether running in headless mode")
    processing_mode: str = Field(..., description="Processing mode (e.g., sequential_production_api)")
    production_features: bool = Field(..., description="Whether production features are available")
    scraper_type: str = Field(..., description="Type of scraper used (ProductionCVScraper or CVLibraryScraper)")


class SessionStatistics(BaseModel):
    """Comprehensive session statistics (production_runner.py pattern)."""
    start_time: float = Field(..., description="Session start timestamp")
    end_time: Optional[float] = Field(None, description="Session end timestamp")
    total_processed: int = Field(default=0, description="Total candidates processed")
    successful_downloads: int = Field(default=0, description="Number of successful downloads")
    failed_downloads: int = Field(default=0, description="Number of failed downloads")
    average_time_per_cv: float = Field(default=0.0, description="Average time per CV processed")
    keywords_used: List[str] = Field(default_factory=list, description="Keywords used in search")
    location_used: Optional[str] = Field(None, description="Location filter used")
    phase: str = Field(default="initializing", description="Current processing phase")
    current_operation: str = Field(default="", description="Current operation description")


class ScrapingProgress(BaseModel):
    """Enhanced scraping progress with production-level details."""
    phase: str = Field(..., description="Current phase (authentication, searching, downloading, completed, failed)")
    total_candidates_found: Optional[int] = Field(None, description="Total candidates found in search")
    total_to_download: Optional[int] = Field(None, description="Total CVs scheduled for download")
    downloaded: int = Field(default=0, description="Number of CVs downloaded so far")
    failed: int = Field(default=0, description="Number of failed downloads")
    current_operation: Optional[str] = Field(None, description="Description of current operation")
    percentage: float = Field(default=0.0, description="Overall completion percentage")
    session_stats: Optional[SessionStatistics] = Field(None, description="Detailed session statistics")


class DownloadedFile(BaseModel):
    """Information about a downloaded CV file."""
    file_id: str = Field(..., description="Unique identifier for the file")
    candidate_name: str = Field(..., description="Name of the candidate")
    filename: str = Field(..., description="Name of the downloaded file")
    file_path: str = Field(..., description="Path to the downloaded file")
    file_size: int = Field(default=0, description="Size of the file in bytes")
    file_format: str = Field(default="pdf", description="File format")
    download_timestamp: float = Field(..., description="Timestamp when file was downloaded")


class ScrapingResults(BaseModel):
    """Comprehensive scraping results (production_runner.py pattern)."""
    downloaded_files: List[str] = Field(default_factory=list, description="Paths to downloaded files")
    candidate_names: List[str] = Field(default_factory=list, description="Names of candidates")
    success_rate: float = Field(default=0.0, description="Download success rate percentage")


class ScrapeResponse(BaseModel):
    """Response model for scrape operations with production-level reporting."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    scrape_id: Optional[str] = Field(None, description="Unique identifier for the scrape operation")
    session_id: Optional[str] = Field(None, description="Session identifier")
    status: str = Field(default="pending", description="Current status of the operation")
    
    # Production-level reporting
    session_duration: Optional[float] = Field(None, description="Total session duration in seconds")
    statistics: Optional[SessionStatistics] = Field(None, description="Comprehensive session statistics")
    performance_metrics: Optional[ProductionMetrics] = Field(None, description="Production performance metrics")
    production_config: Optional[ProductionConfig] = Field(None, description="Production environment configuration")
    
    # Progress and results
    progress: Optional[ScrapingProgress] = Field(None, description="Current progress information")
    results: Optional[ScrapingResults] = Field(None, description="Scraping results when completed")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    # Timestamps
    created_at: Optional[float] = Field(None, description="Operation creation timestamp")
    last_updated: Optional[float] = Field(None, description="Last update timestamp")


class SessionInfo(BaseModel):
    """Information about an active session with production enhancements."""
    session_id: str = Field(..., description="Unique session identifier")
    is_authenticated: bool = Field(..., description="Whether the session is authenticated")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    expires_at: datetime = Field(..., description="Session expiration timestamp")
    active_scrapes: int = Field(default=0, description="Number of active scrape operations")
    total_scrapes: int = Field(default=0, description="Total scrape operations performed")
    total_downloads: int = Field(default=0, description="Total successful downloads")


class SessionListResponse(BaseModel):
    """Response for session listing."""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    sessions: List[SessionInfo] = Field(..., description="List of active sessions")
    total_sessions: int = Field(..., description="Total number of sessions")
    active_sessions: int = Field(..., description="Number of active sessions")


class ScrapeListItem(BaseModel):
    """Summary information for a scrape operation in listings."""
    scrape_id: str = Field(..., description="Unique scrape identifier")
    session_id: str = Field(..., description="Associated session identifier")
    status: str = Field(..., description="Current status")
    keywords: List[str] = Field(default_factory=list, description="Search keywords used")
    location: Optional[str] = Field(None, description="Location filter used")
    created_at: float = Field(..., description="Creation timestamp")
    last_updated: float = Field(..., description="Last update timestamp")
    total_found: Optional[int] = Field(None, description="Total candidates found")
    downloaded: int = Field(default=0, description="Number of CVs downloaded")
    success_rate: Optional[float] = Field(None, description="Download success rate")


class ScrapeListResponse(BaseModel):
    """Response for scrape operation listings."""
    success: bool = Field(..., description="Whether the request was successful")
    scrapes: List[ScrapeListItem] = Field(..., description="List of scrape operations")
    total_count: int = Field(..., description="Total number of scrape operations")
    session_id: str = Field(..., description="Session identifier")


class HealthResponse(BaseModel):
    """Health check response with production metrics."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field(default="1.0.0", description="API version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    cpu_percent: float = Field(..., description="CPU usage percentage")
    active_sessions: int = Field(default=0, description="Number of active sessions")
    active_scrapes: int = Field(default=0, description="Number of active scrape operations")
    production_features: bool = Field(default=False, description="Whether production features are available")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking") 