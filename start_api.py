#!/usr/bin/env python3
"""
Startup script for the CV-Library Scraper API.
"""

import uvicorn
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.core.config import get_settings


def main():
    """Main startup function."""
    settings = get_settings()
    
    print("🚀 Starting CV-Library Scraper API")
    print(f"📡 Server: {settings.host}:{settings.port}")
    print(f"🔧 Debug mode: {settings.debug}")
    print(f"📋 Max concurrent sessions: {settings.max_concurrent_sessions}")
    print("📖 API Documentation: http://localhost:8000/docs")
    print()
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main() 