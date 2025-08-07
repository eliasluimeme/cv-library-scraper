"""
Health check endpoints for monitoring API status and performance.
"""

import logging
import time
import psutil
from datetime import datetime
from fastapi import APIRouter, Request

from api.models.responses import HealthResponse
from api.core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Track service start time for uptime calculation
service_start_time = time.time()


@router.get("/")
async def health_check(request: Request):
    """
    Comprehensive health check endpoint.
    Returns system status, resource usage, and performance metrics.
    """
    try:
        settings = get_settings()
        current_time = time.time()
        uptime = current_time - service_start_time
        
        # Get system resources
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get session manager and scraper service from app state
        session_manager = getattr(request.app.state, 'session_manager', None)
        scraper_service = getattr(request.app.state, 'scraper_service', None)
        production_features = getattr(request.app.state, 'production_features', False)
        
        # Count active sessions and scrapes
        active_sessions = 0
        active_scrapes = 0
        
        if session_manager:
            try:
                stats = session_manager.get_session_stats()
                active_sessions = stats.get('active_sessions', 0)
            except Exception as e:
                logger.error(f"Error getting session stats: {e}")
        
        if scraper_service:
            try:
                # Count active scrapes from scraper service
                active_scrapes = len(scraper_service._active_scrapes)
            except Exception as e:
                logger.error(f"Error getting scrape stats: {e}")
        
        # Overall health status
        overall_status = "healthy"
        if cpu_percent > 90 or memory.percent > 95:
            overall_status = "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            uptime_seconds=uptime,
            memory_usage_mb=memory.used / (1024 * 1024),
            cpu_percent=cpu_percent,
            active_sessions=active_sessions,
            active_scrapes=active_scrapes,
            production_features=production_features
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        return HealthResponse(
            status="error",
            timestamp=datetime.utcnow(),
            version="unknown",
            uptime_seconds=0.0,
            memory_usage_mb=0.0,
            cpu_percent=0.0,
            active_sessions=0,
            active_scrapes=0,
            production_features=False
        )


@router.get("/simple/")
async def simple_health_check():
    """Simple health check that just returns OK."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/ready/")
async def readiness_check(request: Request):
    """
    Readiness check for container orchestration.
    Returns 200 if the service is ready to handle requests.
    """
    try:
        # Check if critical services are available
        session_manager = getattr(request.app.state, 'session_manager', None)
        scraper_service = getattr(request.app.state, 'scraper_service', None)
        
        if not session_manager or not scraper_service:
            return {"status": "not_ready", "reason": "Services not initialized"}, 503
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "error": str(e)}, 503


@router.get("/live/")
async def liveness_check():
    """
    Liveness check for container orchestration.
    Returns 200 if the service is alive.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()} 