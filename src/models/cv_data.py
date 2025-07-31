"""
Data models for CV and candidate information.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


@dataclass
class CandidateInfo:
    """Information about a candidate extracted from CV preview."""
    
    candidate_id: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    salary_expectation: Optional[str] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    availability: Optional[str] = None
    last_active: Optional[str] = None
    contact_info: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert candidate info to dictionary."""
        return {
            'candidate_id': self.candidate_id,
            'name': self.name,
            'title': self.title,
            'location': self.location,
            'salary_expectation': self.salary_expectation,
            'experience_years': self.experience_years,
            'education': self.education,
            'skills': self.skills,
            'summary': self.summary,
            'availability': self.availability,
            'last_active': self.last_active,
            'contact_info': self.contact_info
        }


@dataclass
class CVData:
    """Complete CV data including metadata and download information."""
    
    # CV Metadata
    cv_id: Optional[str] = None
    url: Optional[str] = None
    candidate: Optional[CandidateInfo] = None
    
    # Search Context
    search_keywords: List[str] = field(default_factory=list)
    search_location: Optional[str] = None
    search_timestamp: Optional[datetime] = None
    
    # Download Information
    download_status: str = "pending"  # pending, downloading, completed, failed
    download_timestamp: Optional[datetime] = None
    file_path: Optional[Path] = None
    file_format: Optional[str] = None
    file_size: Optional[int] = None
    
    # Processing Information
    processed: bool = False
    processing_timestamp: Optional[datetime] = None
    extraction_confidence: Optional[float] = None
    quality_score: Optional[float] = None
    
    # Error Handling
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.search_timestamp is None:
            self.search_timestamp = datetime.now()
        
        if self.candidate is None:
            self.candidate = CandidateInfo()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert CV data to dictionary for serialization."""
        return {
            'cv_id': self.cv_id,
            'url': self.url,
            'candidate': self.candidate.to_dict() if self.candidate else None,
            'search_keywords': self.search_keywords,
            'search_location': self.search_location,
            'search_timestamp': self.search_timestamp.isoformat() if self.search_timestamp else None,
            'download_status': self.download_status,
            'download_timestamp': self.download_timestamp.isoformat() if self.download_timestamp else None,
            'file_path': str(self.file_path) if self.file_path else None,
            'file_format': self.file_format,
            'file_size': self.file_size,
            'processed': self.processed,
            'processing_timestamp': self.processing_timestamp.isoformat() if self.processing_timestamp else None,
            'extraction_confidence': self.extraction_confidence,
            'quality_score': self.quality_score,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CVData':
        """Create CVData instance from dictionary."""
        cv_data = cls()
        
        cv_data.cv_id = data.get('cv_id')
        cv_data.url = data.get('url')
        cv_data.search_keywords = data.get('search_keywords', [])
        cv_data.search_location = data.get('search_location')
        cv_data.download_status = data.get('download_status', 'pending')
        cv_data.file_format = data.get('file_format')
        cv_data.file_size = data.get('file_size')
        cv_data.processed = data.get('processed', False)
        cv_data.extraction_confidence = data.get('extraction_confidence')
        cv_data.quality_score = data.get('quality_score')
        cv_data.error_message = data.get('error_message')
        cv_data.retry_count = data.get('retry_count', 0)
        
        # Handle datetime fields
        if data.get('search_timestamp'):
            cv_data.search_timestamp = datetime.fromisoformat(data['search_timestamp'])
        if data.get('download_timestamp'):
            cv_data.download_timestamp = datetime.fromisoformat(data['download_timestamp'])
        if data.get('processing_timestamp'):
            cv_data.processing_timestamp = datetime.fromisoformat(data['processing_timestamp'])
        
        # Handle file path
        if data.get('file_path'):
            cv_data.file_path = Path(data['file_path'])
        
        # Handle candidate info
        if data.get('candidate'):
            candidate_data = data['candidate']
            cv_data.candidate = CandidateInfo(
                candidate_id=candidate_data.get('candidate_id'),
                name=candidate_data.get('name'),
                title=candidate_data.get('title'),
                location=candidate_data.get('location'),
                salary_expectation=candidate_data.get('salary_expectation'),
                experience_years=candidate_data.get('experience_years'),
                education=candidate_data.get('education'),
                skills=candidate_data.get('skills', []),
                summary=candidate_data.get('summary'),
                availability=candidate_data.get('availability'),
                last_active=candidate_data.get('last_active'),
                contact_info=candidate_data.get('contact_info', {})
            )
        
        return cv_data
    
    def mark_downloaded(self, file_path: Path, file_format: str, file_size: int):
        """Mark CV as successfully downloaded."""
        self.download_status = "completed"
        self.download_timestamp = datetime.now()
        self.file_path = file_path
        self.file_format = file_format
        self.file_size = file_size
    
    def mark_failed(self, error_message: str):
        """Mark CV download as failed."""
        self.download_status = "failed"
        self.error_message = error_message
        self.retry_count += 1
    
    def mark_processing_complete(self, confidence: float, quality_score: float):
        """Mark CV processing as complete."""
        self.processed = True
        self.processing_timestamp = datetime.now()
        self.extraction_confidence = confidence
        self.quality_score = quality_score
    
    def generate_filename(self, keywords: List[str] = None) -> str:
        """
        Generate a standardized filename for the CV.
        
        Args:
            keywords: Optional keywords to include in filename
            
        Returns:
            Generated filename string
        """
        # Use search keywords if not provided
        if keywords is None:
            keywords = self.search_keywords
        
        # Create base filename components
        components = []
        
        # Add timestamp
        if self.search_timestamp:
            timestamp = self.search_timestamp.strftime("%Y%m%d_%H%M%S")
            components.append(timestamp)
        
        # Add candidate name if available
        if self.candidate and self.candidate.name:
            # Clean name for filename
            clean_name = "".join(c for c in self.candidate.name if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_name = "_".join(clean_name.split())
            components.append(clean_name[:30])  # Limit length
        
        # Add candidate ID if available
        if self.cv_id:
            components.append(f"ID_{self.cv_id}")
        
        # Add keywords (first few)
        if keywords:
            keyword_str = "_".join(keywords[:2])  # Limit to first 2 keywords
            keyword_str = "".join(c for c in keyword_str if c.isalnum() or c in ('_', '-'))
            components.append(keyword_str[:20])  # Limit length
        
        # Join components and add extension
        filename = "_".join(components)
        
        # Ensure filename isn't too long (limit to 100 chars before extension)
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename
    
    def is_duplicate_of(self, other: 'CVData') -> bool:
        """
        Check if this CV is a duplicate of another CV.
        
        Args:
            other: Another CVData instance to compare with
            
        Returns:
            True if CVs are considered duplicates
        """
        # Compare by CV ID if available
        if self.cv_id and other.cv_id:
            return self.cv_id == other.cv_id
        
        # Compare by candidate name and basic info
        if (self.candidate and other.candidate and 
            self.candidate.name and other.candidate.name):
            
            # Names match
            names_match = self.candidate.name.lower().strip() == other.candidate.name.lower().strip()
            
            # Locations match (if available)
            locations_match = True
            if self.candidate.location and other.candidate.location:
                locations_match = self.candidate.location.lower().strip() == other.candidate.location.lower().strip()
            
            # Titles are similar (if available)
            titles_similar = True
            if self.candidate.title and other.candidate.title:
                title1 = self.candidate.title.lower().strip()
                title2 = other.candidate.title.lower().strip()
                # Basic similarity check - could be enhanced
                titles_similar = title1 == title2 or title1 in title2 or title2 in title1
            
            return names_match and locations_match and titles_similar
        
        # Compare by URL if available
        if self.url and other.url:
            return self.url == other.url
        
        return False 