"""
Data models for search results and collections.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Iterator
from datetime import datetime

from .cv_data import CVData


@dataclass
class SearchResult:
    """Individual search result item from CV-Library."""
    
    # Basic Information
    cv_id: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    summary: Optional[str] = None
    
    # URLs and Links
    profile_url: Optional[str] = None
    cv_preview_url: Optional[str] = None
    download_url: Optional[str] = None
    
    # Metadata
    last_active: Optional[str] = None
    experience_level: Optional[str] = None
    availability: Optional[str] = None
    
    # Search Context
    search_rank: Optional[int] = None
    search_score: Optional[float] = None
    search_keywords: List[str] = field(default_factory=list)
    search_location: Optional[str] = None
    
    # Additional Details
    skills: List[str] = field(default_factory=list)
    qualifications: List[str] = field(default_factory=list)
    industry: Optional[str] = None
    
    # Processing Flags
    processed: bool = False
    selected_for_download: bool = False
    
    def to_cv_data(self) -> CVData:
        """Convert search result to CVData object."""
        cv_data = CVData()
        
        # Basic mapping
        cv_data.cv_id = self.cv_id
        cv_data.url = self.profile_url or self.cv_preview_url
        cv_data.search_keywords = self.search_keywords.copy()
        cv_data.search_location = self.search_location
        
        # Candidate information
        cv_data.candidate.candidate_id = self.cv_id
        cv_data.candidate.name = self.name
        cv_data.candidate.title = self.title
        cv_data.candidate.location = self.location
        cv_data.candidate.salary_expectation = self.salary
        cv_data.candidate.summary = self.summary
        cv_data.candidate.availability = self.availability
        cv_data.candidate.last_active = self.last_active
        cv_data.candidate.skills = self.skills.copy()
        
        return cv_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            'cv_id': self.cv_id,
            'title': self.title,
            'name': self.name,
            'location': self.location,
            'salary': self.salary,
            'summary': self.summary,
            'profile_url': self.profile_url,
            'cv_preview_url': self.cv_preview_url,
            'download_url': self.download_url,
            'last_active': self.last_active,
            'experience_level': self.experience_level,
            'availability': self.availability,
            'search_rank': self.search_rank,
            'search_score': self.search_score,
            'search_keywords': self.search_keywords,
            'search_location': self.search_location,
            'skills': self.skills,
            'qualifications': self.qualifications,
            'industry': self.industry,
            'processed': self.processed,
            'selected_for_download': self.selected_for_download
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create SearchResult from dictionary."""
        return cls(
            cv_id=data.get('cv_id'),
            title=data.get('title'),
            name=data.get('name'),
            location=data.get('location'),
            salary=data.get('salary'),
            summary=data.get('summary'),
            profile_url=data.get('profile_url'),
            cv_preview_url=data.get('cv_preview_url'),
            download_url=data.get('download_url'),
            last_active=data.get('last_active'),
            experience_level=data.get('experience_level'),
            availability=data.get('availability'),
            search_rank=data.get('search_rank'),
            search_score=data.get('search_score'),
            search_keywords=data.get('search_keywords', []),
            search_location=data.get('search_location'),
            skills=data.get('skills', []),
            qualifications=data.get('qualifications', []),
            industry=data.get('industry'),
            processed=data.get('processed', False),
            selected_for_download=data.get('selected_for_download', False)
        )
    
    def matches_keywords(self, keywords: List[str], case_sensitive: bool = False) -> bool:
        """
        Check if this result matches any of the given keywords.
        
        Args:
            keywords: List of keywords to match against
            case_sensitive: Whether to perform case-sensitive matching
            
        Returns:
            True if any keyword matches
        """
        if not keywords:
            return True
        
        # Combine searchable text
        searchable_text = " ".join(filter(None, [
            self.title, self.name, self.summary, self.industry,
            " ".join(self.skills), " ".join(self.qualifications)
        ]))
        
        if not case_sensitive:
            searchable_text = searchable_text.lower()
            keywords = [k.lower() for k in keywords]
        
        # Check if any keyword appears in the text
        return any(keyword in searchable_text for keyword in keywords)


@dataclass
class SearchResultCollection:
    """Collection of search results with metadata and filtering capabilities."""
    
    results: List[SearchResult] = field(default_factory=list)
    search_query: Optional[str] = None
    search_keywords: List[str] = field(default_factory=list)
    search_location: Optional[str] = None
    search_timestamp: Optional[datetime] = None
    total_found: Optional[int] = None
    page_number: int = 1
    results_per_page: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.search_timestamp is None:
            self.search_timestamp = datetime.now()
        
        # Set search context for all results
        for i, result in enumerate(self.results):
            result.search_keywords = self.search_keywords.copy()
            result.search_location = self.search_location
            result.search_rank = i + 1 + (self.page_number - 1) * (self.results_per_page or len(self.results))
    
    def __len__(self) -> int:
        """Return number of results."""
        return len(self.results)
    
    def __iter__(self) -> Iterator[SearchResult]:
        """Iterate over results."""
        return iter(self.results)
    
    def __getitem__(self, index: int) -> SearchResult:
        """Get result by index."""
        return self.results[index]
    
    def add_result(self, result: SearchResult):
        """Add a result to the collection."""
        result.search_keywords = self.search_keywords.copy()
        result.search_location = self.search_location
        result.search_rank = len(self.results) + 1
        self.results.append(result)
    
    def filter_by_keywords(self, keywords: List[str], case_sensitive: bool = False) -> 'SearchResultCollection':
        """
        Filter results by keywords.
        
        Args:
            keywords: Keywords to filter by
            case_sensitive: Whether to perform case-sensitive filtering
            
        Returns:
            New collection with filtered results
        """
        filtered_results = [
            result for result in self.results 
            if result.matches_keywords(keywords, case_sensitive)
        ]
        
        new_collection = SearchResultCollection(
            results=filtered_results,
            search_query=self.search_query,
            search_keywords=self.search_keywords.copy(),
            search_location=self.search_location,
            search_timestamp=self.search_timestamp,
            page_number=self.page_number
        )
        
        return new_collection
    
    def filter_by_location(self, location: str, exact_match: bool = False) -> 'SearchResultCollection':
        """
        Filter results by location.
        
        Args:
            location: Location to filter by
            exact_match: Whether to require exact location match
            
        Returns:
            New collection with filtered results
        """
        if exact_match:
            filtered_results = [
                result for result in self.results 
                if result.location and result.location.lower().strip() == location.lower().strip()
            ]
        else:
            filtered_results = [
                result for result in self.results 
                if result.location and location.lower() in result.location.lower()
            ]
        
        new_collection = SearchResultCollection(
            results=filtered_results,
            search_query=self.search_query,
            search_keywords=self.search_keywords.copy(),
            search_location=self.search_location,
            search_timestamp=self.search_timestamp,
            page_number=self.page_number
        )
        
        return new_collection
    
    def sort_by_relevance(self, reverse: bool = True) -> 'SearchResultCollection':
        """Sort results by relevance score."""
        sorted_results = sorted(
            self.results, 
            key=lambda x: x.search_score or 0, 
            reverse=reverse
        )
        
        new_collection = SearchResultCollection(
            results=sorted_results,
            search_query=self.search_query,
            search_keywords=self.search_keywords.copy(),
            search_location=self.search_location,
            search_timestamp=self.search_timestamp,
            page_number=self.page_number
        )
        
        return new_collection
    
    def get_top_results(self, count: int) -> 'SearchResultCollection':
        """Get top N results."""
        top_results = self.results[:count]
        
        new_collection = SearchResultCollection(
            results=top_results,
            search_query=self.search_query,
            search_keywords=self.search_keywords.copy(),
            search_location=self.search_location,
            search_timestamp=self.search_timestamp,
            page_number=self.page_number
        )
        
        return new_collection
    
    def select_for_download(self, indices: List[int]):
        """Mark specific results for download."""
        for index in indices:
            if 0 <= index < len(self.results):
                self.results[index].selected_for_download = True
    
    def get_selected_results(self) -> List[SearchResult]:
        """Get results selected for download."""
        return [result for result in self.results if result.selected_for_download]
    
    def to_cv_data_list(self) -> List[CVData]:
        """Convert all results to CVData objects."""
        return [result.to_cv_data() for result in self.results]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary."""
        return {
            'results': [result.to_dict() for result in self.results],
            'search_query': self.search_query,
            'search_keywords': self.search_keywords,
            'search_location': self.search_location,
            'search_timestamp': self.search_timestamp.isoformat() if self.search_timestamp else None,
            'total_found': self.total_found,
            'page_number': self.page_number,
            'results_per_page': self.results_per_page,
            'count': len(self.results)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResultCollection':
        """Create collection from dictionary."""
        results = [SearchResult.from_dict(result_data) for result_data in data.get('results', [])]
        
        collection = cls(
            results=results,
            search_query=data.get('search_query'),
            search_keywords=data.get('search_keywords', []),
            search_location=data.get('search_location'),
            total_found=data.get('total_found'),
            page_number=data.get('page_number', 1),
            results_per_page=data.get('results_per_page')
        )
        
        if data.get('search_timestamp'):
            collection.search_timestamp = datetime.fromisoformat(data['search_timestamp'])
        
        return collection 