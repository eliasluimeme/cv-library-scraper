"""
Scrape router - Production-ready CV scraping endpoints with comprehensive reporting
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query

from api.models.requests import ScrapeRequest
from api.models.responses import (
    ScrapeResponse, ScrapeListResponse, ScrapeListItem, 
    ProductionMetrics, ProductionConfig, SessionStatistics,
    ScrapingProgress, ScrapingResults
)
from api.services.session_manager import SessionManager
from api.services.scraper_service import ScraperService


router = APIRouter()
logger = logging.getLogger(__name__)


def get_scraper_service(request: Request) -> ScraperService:
    """Get scraper service from app state."""
    return request.app.state.scraper_service


def get_session_manager(request: Request) -> SessionManager:
    """Get session manager from app state."""
    return request.app.state.session_manager


def _convert_scrape_data_to_response(scrape_data: dict, scrape_id: str) -> ScrapeResponse:
    """Convert internal scrape data to API response format."""
    
    # Extract session statistics
    session_stats = scrape_data.get('session_stats', {})
    statistics = SessionStatistics(
        start_time=session_stats.get('start_time', 0),
        end_time=session_stats.get('end_time'),
        total_processed=session_stats.get('total_processed', 0),
        successful_downloads=session_stats.get('successful_downloads', 0),
        failed_downloads=session_stats.get('failed_downloads', 0),
        average_time_per_cv=session_stats.get('average_time_per_cv', 0.0),
        keywords_used=session_stats.get('keywords_used', []),
        location_used=session_stats.get('location_used'),
        phase=session_stats.get('phase', 'unknown'),
        current_operation=session_stats.get('current_operation', '')
    )
    
    # Extract progress information
    progress = ScrapingProgress(
        phase=session_stats.get('phase', 'unknown'),
        total_candidates_found=session_stats.get('total_processed'),
        total_to_download=session_stats.get('total_processed'),
        downloaded=session_stats.get('successful_downloads', 0),
        failed=session_stats.get('failed_downloads', 0),
        current_operation=session_stats.get('current_operation', ''),
        percentage=100.0 if session_stats.get('phase') == 'completed' else 0.0,
        session_stats=statistics
    )
    
    # Extract production metrics from result if available
    result = scrape_data.get('result', {})
    performance_metrics = None
    production_config = None
    session_duration = None
    scraping_results = None
    
    if result:
        # Performance metrics
        perf_data = result.get('performance_metrics', {})
        if perf_data:
            # Handle potential string formatting in performance data
            avg_time = perf_data.get('avg_time_per_operation', '0.0s')
            total_ops = perf_data.get('total_operations', 0)
            success_rate = perf_data.get('success_rate', 100.0)
            
            # Parse success rate if it's a string with %
            if isinstance(success_rate, str) and success_rate.endswith('%'):
                success_rate = float(success_rate.rstrip('%'))
            elif isinstance(success_rate, str):
                success_rate = float(success_rate)
            
            performance_metrics = ProductionMetrics(
                avg_time_per_operation=avg_time,
                total_operations=total_ops,
                success_rate=success_rate
            )
        
        # Production configuration
        prod_config = result.get('production_config', {})
        if prod_config:
            production_config = ProductionConfig(
                headless_mode=prod_config.get('headless_mode', False),
                processing_mode=prod_config.get('processing_mode', 'standard'),
                production_features=prod_config.get('production_features', False),
                scraper_type=prod_config.get('scraper_type', 'CVLibraryScraper')
            )
        
        # Session duration
        session_duration = result.get('session_duration')
        
        # Scraping results
        results_data = result.get('results', {})
        if results_data:
            scraping_results = ScrapingResults(
                downloaded_files=results_data.get('downloaded_files', []),
                candidate_names=results_data.get('candidate_names', []),
                success_rate=results_data.get('success_rate', 0.0)
            )
    
    return ScrapeResponse(
        success=scrape_data.get('status') == 'completed',
        message=f"Scrape operation {scrape_data.get('status', 'unknown')}",
        scrape_id=scrape_id,
        session_id=scrape_data.get('session_id'),
        status=scrape_data.get('status', 'unknown'),
        session_duration=session_duration,
        statistics=statistics,
        performance_metrics=performance_metrics,
        production_config=production_config,
        progress=progress,
        results=scraping_results,
        error=scrape_data.get('error'),
        created_at=scrape_data.get('created_at'),
        last_updated=scrape_data.get('last_updated')
    )


@router.post("/")
async def scrape_cvs(
    scrape_request: ScrapeRequest,
    scraper_service: ScraperService = Depends(get_scraper_service),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Initiate a comprehensive CV scraping operation (search + download) with production-level reporting.
    
    This endpoint combines search and download into a single operation using the same 
    production-ready logic as the CLI tools for maximum reliability and consistency.
    """
    try:
        # Validate session exists and is authenticated
        session_data = session_manager.get_session(scrape_request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session_data.is_authenticated:
            raise HTTPException(status_code=401, detail="Session not authenticated")
        
        logger.info(f"Starting production scrape operation for session {scrape_request.session_id}")
        
        # Initiate scraping operation
        scrape_id = await scraper_service.scrape_cvs(scrape_request)
        
        return ScrapeResponse(
            success=True,
            message="Scraping operation initiated with production-ready features",
            scrape_id=scrape_id,
            session_id=scrape_request.session_id,
            status="pending",
            created_at=scrape_data.get('created_at') if 'scrape_data' in locals() else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate scrape operation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping: {str(e)}")


@router.get("/{scrape_id}/")
async def get_scrape_status(
    scrape_id: str,
    scraper_service: ScraperService = Depends(get_scraper_service)
):
    """
    Get detailed status and results of a scraping operation with production-level metrics.
    
    Returns comprehensive information including session statistics, performance metrics,
    and production configuration details.
    """
    try:
        scrape_data = scraper_service.get_scrape_status(scrape_id)
        
        if not scrape_data:
            raise HTTPException(status_code=404, detail="Scrape operation not found")
        
        return _convert_scrape_data_to_response(scrape_data, scrape_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scrape status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/session/{session_id}/list/")
async def list_session_scrapes(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of scrapes to return"),
    offset: int = Query(default=0, ge=0, description="Number of scrapes to skip"),
    scraper_service: ScraperService = Depends(get_scraper_service),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    List all scraping operations for a session with production-level summary information.
    
    Returns paginated list of scrape operations with summary statistics and performance data.
    """
    try:
        # Validate session exists
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get scrapes for the session
        scrapes_data = scraper_service.list_scrapes(session_id, limit, offset)
        
        # Convert to response format
        scrape_items = []
        for scrape_data in scrapes_data:
            session_stats = scrape_data.get('session_stats', {})
            result = scrape_data.get('result', {})
            
            # Calculate success rate if available
            success_rate = None
            if result and result.get('results'):
                success_rate = result['results'].get('success_rate')
            
            scrape_item = ScrapeListItem(
                scrape_id=scrape_data['id'],
                session_id=scrape_data['session_id'],
                status=scrape_data['status'],
                keywords=session_stats.get('keywords_used', []),
                location=session_stats.get('location_used'),
                created_at=scrape_data['created_at'],
                last_updated=scrape_data['last_updated'],
                total_found=session_stats.get('total_processed'),
                downloaded=session_stats.get('successful_downloads', 0),
                success_rate=success_rate
            )
            scrape_items.append(scrape_item)
        
        return ScrapeListResponse(
            success=True,
            scrapes=scrape_items,
            total_count=len(scrape_items),
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list scrapes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list scrapes: {str(e)}") 