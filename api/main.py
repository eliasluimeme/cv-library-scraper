"""
CV-Library Scraper API - Main FastAPI Application with Production-Ready Features
Enhanced with production environment setup and comprehensive monitoring
"""

import logging
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.core.config import get_settings
from api.core.logging_config import setup_logging
from api.routers import auth, scrape, sessions, health
from api.services.session_manager import SessionManager
from api.services.scraper_service import ScraperService

# Import production enhancements
try:
    from src.config.production_settings import (
        PRODUCTION_CONFIG, 
        PRODUCTION_OPTIMIZER, 
        PERFORMANCE_MONITOR
    )
    PRODUCTION_FEATURES_AVAILABLE = True
except ImportError:
    PRODUCTION_FEATURES_AVAILABLE = False
    # Simple fallback objects
    class SimpleConfig:
        HEADLESS_PRODUCTION = False
    class SimpleOptimizer:
        def setup_logging(self): pass
    class SimpleMonitor:
        def start_operation(self): pass
        def end_operation(self, success=True): pass
        def get_performance_summary(self): return {'avg_time_per_operation': '0.0s'}
    
    PRODUCTION_CONFIG = SimpleConfig()
    PRODUCTION_OPTIMIZER = SimpleOptimizer()
    PERFORMANCE_MONITOR = SimpleMonitor()


def setup_production_environment():
    """Setup production environment for API operations (mirroring production_runner.py)."""
    logger = logging.getLogger(__name__)
    
    if PRODUCTION_FEATURES_AVAILABLE:
        logger.info("🚀 Setting up production environment for API...")
        
        # Configure production logging
        PRODUCTION_OPTIMIZER.setup_logging()
        
        # Set environment variables for production
        os.environ['CV_SCRAPER_MODE'] = 'production_api'
        os.environ['BROWSER_HEADLESS'] = str(PRODUCTION_CONFIG.HEADLESS_PRODUCTION)
    
    # Create output directories (always do this regardless of production features)
    Path("downloaded_cvs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    if PRODUCTION_FEATURES_AVAILABLE:
        logger.info("✅ Production environment configured for API")
    else:
        logger.info("ℹ️  API running in standard mode (production features not available)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events with production setup."""
    # Startup
    settings = get_settings()
    
    # Setup production environment first (before logging)
    setup_production_environment()
    
    # Then setup logging
    setup_logging(settings.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting CV-Library Scraper API with Production Features")
    
    if PRODUCTION_FEATURES_AVAILABLE:
        logger.info("🎯 Production features enabled:")
        logger.info(f"   • Headless mode: {PRODUCTION_CONFIG.HEADLESS_PRODUCTION}")
        logger.info("   • Performance monitoring: Active")
        logger.info("   • Production logging: Configured")
        logger.info("   • Session statistics: Enhanced")
    
    # Initialize services with production enhancements
    session_manager = SessionManager()
    scraper_service = ScraperService(session_manager)
    
    # Store services in app state
    app.state.session_manager = session_manager
    app.state.scraper_service = scraper_service
    
    # Store production features status for health checks
    app.state.production_features = PRODUCTION_FEATURES_AVAILABLE
    
    logger.info("✅ API services initialized with production enhancements")
    
    yield
    
    # Shutdown
    logger.info("🧹 Shutting down CV-Library Scraper API")
    await session_manager.cleanup_all_sessions()
    await scraper_service.cleanup()
    logger.info("✅ Production cleanup completed")


# Initialize FastAPI app with production configuration
app = FastAPI(
    title="CV-Library Scraper API - Production Ready",
    description="REST API for automated CV scraping from CV-Library recruiter portal with production-level reliability and monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)


# Global exception handler with production-level error reporting
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors with production logging."""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception in production API: {exc}", exc_info=True)
    
    # Enhanced error response for production
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred in the production API",
            "request_id": getattr(request.state, "request_id", None),
            "production_mode": PRODUCTION_FEATURES_AVAILABLE,
            "timestamp": str(logger.root.handlers[0].formatter.formatTime(logger.makeRecord("error", 50, "", 0, "", (), None)))
        }
    )


# Include routers with production-ready endpoints
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(scrape.router, prefix="/api/v1/scrape", tags=["Production Scraping"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Session Management"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health & Monitoring"])


@app.get("/")
async def root():
    """Root endpoint with API information and production status."""
    return {
        "name": "CV-Library Scraper API - Production Ready",
        "version": "1.0.0",
        "status": "operational",
        "production_features": PRODUCTION_FEATURES_AVAILABLE,
        "processing_mode": "sequential_production_api" if PRODUCTION_FEATURES_AVAILABLE else "standard",
        "docs": "/docs",
        "health": "/api/v1/health",
        "scraper_type": "ProductionCVScraper" if PRODUCTION_FEATURES_AVAILABLE else "CVLibraryScraper"
    }


if __name__ == "__main__":
    settings = get_settings()
    
    # Production startup message
    print("🚀 Starting CV-Library Scraper API - Production Ready")
    if PRODUCTION_FEATURES_AVAILABLE:
        print("🎯 Production features: ENABLED")
    else:
        print("ℹ️  Production features: Not available (using standard mode)")
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 