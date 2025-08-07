"""
Session management endpoints for listing and managing active sessions.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Request, Query

from api.models.responses import SessionListResponse, SessionInfo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def list_sessions(request: Request):
    """List all active sessions."""
    try:
        session_manager = request.app.state.session_manager
        sessions_data = session_manager.list_sessions()
        stats = session_manager.get_session_stats()
        
        # Convert SessionData to SessionInfo
        sessions = []
        for session_dict in sessions_data:
            session_info = SessionInfo(
                session_id=session_dict['session_id'],
                status=session_dict['status'],
                created_at=session_dict['created_at'],
                last_activity=session_dict['last_activity'],
                expires_at=session_dict.get('expires_at'),
                active_scrapes=session_dict.get('active_scrapes', 0),
                total_downloads=session_dict.get('total_downloads', 0),
                total_scrapes=session_dict.get('total_scrapes', 0)
            )
            sessions.append(session_info)
        
        return SessionListResponse(
            success=True,
            message="Sessions retrieved",
            sessions=sessions,
            total_sessions=stats.get('total_sessions', 0),
            active_sessions=stats.get('active_sessions', 0)
        )
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/{session_id}/")
async def get_session_details(session_id: str, request: Request):
    """Get detailed information about a specific session."""
    session_manager = request.app.state.session_manager
    scraper_service = request.app.state.scraper_service
    
    session_data = session_manager.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get scrapes for this session
    scrapes = scraper_service.list_scrapes(session_id)
    
    return {
        "success": True,
        "message": "Session details retrieved",
        "session": {
            "session_id": session_data.session_id,
            "status": session_data.status,
            "created_at": session_data.created_at.isoformat(),
            "last_activity": session_data.last_activity.isoformat(),
            "expires_at": session_data.expires_at.isoformat() if session_data.expires_at else None,
            "is_authenticated": session_data.is_authenticated,
            "active_scrapes": len(session_data.active_scrapes),
            "total_downloads": session_data.total_downloads,
            "total_scrapes": session_data.total_scrapes
        },
        "scrapes": scrapes
    }


@router.delete("/{session_id}/")
async def cleanup_session(session_id: str, request: Request):
    """Clean up a specific session."""
    session_manager = request.app.state.session_manager
    
    success = await session_manager.cleanup_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "message": "Session cleaned up successfully"
    } 