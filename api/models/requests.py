"""
Request models for the API endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, validator, Field


class AuthRequest(BaseModel):
    """Authentication request model."""
    username: str = Field(..., description="CV-Library email/username")
    password: str = Field(..., description="CV-Library password")
    remember_session: bool = Field(default=True, description="Keep session alive")


class ScrapeRequest(BaseModel):
    """Request model for CV scraping operations with comprehensive filters."""
    session_id: str = Field(..., description="Session ID for the request")
    keywords: List[str] = Field(..., description="Search keywords", min_items=1)
    location: Optional[str] = Field(None, description="Location filter")
    max_downloads: int = Field(default=25, description="Maximum number of CVs to download", gt=0)
    
    # Salary filters
    salary_min: Optional[str] = Field(None, description="Minimum salary filter (e.g., '30000')")
    salary_max: Optional[str] = Field(None, description="Maximum salary filter (e.g., '50000')")
    
    # Job and industry filters
    job_type: Optional[List[str]] = Field(None, description="Job types (e.g., ['Permanent', 'Contract'])")
    industry: Optional[List[str]] = Field(None, description="Industries (e.g., ['IT/Internet/Technical'])")
    
    # Location and timing filters
    distance: Optional[int] = Field(None, description="Distance in miles from location", ge=1)
    time_period: Optional[str] = Field(None, description="CV submission period in days (e.g., '1', '7', '30')")
    
    # Boolean filters
    willing_to_relocate: Optional[bool] = Field(None, description="Only candidates willing to relocate")
    uk_driving_licence: Optional[bool] = Field(None, description="Only candidates with UK driving licence")
    hide_recently_viewed: Optional[bool] = Field(None, description="Hide recently viewed candidates")
    
    # Advanced filters
    languages: Optional[List[str]] = Field(None, description="Additional languages (e.g., ['French', 'German'])")
    minimum_match: Optional[str] = Field(None, description="Minimum match percentage (e.g., '60', '80')")
    sort_order: Optional[str] = Field(default="relevancy desc", description="Sort order")
    
    # Advanced keyword filters
    must_have_keywords: Optional[str] = Field(None, description="Keywords that must appear")
    any_keywords: Optional[str] = Field(None, description="Any of these keywords")
    none_keywords: Optional[str] = Field(None, description="Keywords that must not appear")
    
    # Download options
    file_formats: List[str] = Field(default=["pdf", "doc", "docx"], description="File formats to download")
    organize_by_keywords: bool = Field(default=False, description="Organize files by keywords")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "abc123",
                "keywords": ["Senior Software Engineer", "Python"],
                "location": "London",
                "max_downloads": 10,
                "salary_min": "50000",
                "salary_max": "80000",
                "job_type": ["Permanent"],
                "industry": ["IT/Internet/Technical"],
                "distance": 25,
                "time_period": "7",
                "willing_to_relocate": False,
                "uk_driving_licence": True,
                "minimum_match": "60",
                "sort_order": "relevancy desc",
                "must_have_keywords": "Python Django",
                "file_formats": ["pdf", "docx"]
            }
        }
    
    @validator("keywords")
    def validate_keywords(cls, v):
        if not v or not any(keyword.strip() for keyword in v):
            raise ValueError("At least one non-empty keyword is required")
        return [keyword.strip() for keyword in v if keyword.strip()]
    
    @validator("file_formats")
    def validate_file_formats(cls, v):
        allowed_formats = {"pdf", "doc", "docx"}
        if v:
            invalid_formats = set(v) - allowed_formats
            if invalid_formats:
                raise ValueError(f"Invalid file formats: {invalid_formats}")
        return v or ["pdf"]


class SessionCleanupRequest(BaseModel):
    """Session cleanup request model."""
    force: bool = Field(False, description="Force cleanup even if active")
    cleanup_files: bool = Field(True, description="Also cleanup downloaded files")


class ScrapingFilterRequest(BaseModel):
    """Request model for getting scraping results with pagination."""
    page: int = Field(1, description="Page number", ge=1)
    page_size: int = Field(20, description="Results per page", ge=1, le=100)
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order: asc or desc")
    
    @validator("sort_order")
    def validate_sort_order(cls, v):
        if v and v.lower() not in ["asc", "desc"]:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v.lower() if v else "desc" 