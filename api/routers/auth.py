"""
Authentication endpoints for CV-Library login and session management.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from api.models.requests import AuthRequest

# Simple authentication response models
class AuthResponse(BaseModel):
    """Authentication response model."""
    success: bool = Field(..., description="Whether authentication was successful")
    message: str = Field(..., description="Response message")
    session_id: Optional[str] = Field(None, description="Session identifier")
    expires_at: Optional[datetime] = Field(None, description="Session expiration time")

class LogoutResponse(BaseModel):
    """Logout response model."""
    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Response message")

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login/")
async def login(auth_request: AuthRequest, request: Request):
    """Authenticate with CV-Library and create a session."""
    try:
        session_manager = request.app.state.session_manager
        scraper_service = request.app.state.scraper_service
        
        # Create session with username for profile generation
        session_id = session_manager.create_session(
            remember_session=auth_request.remember_session,
            username=auth_request.username
        )
        
        # Attempt authentication with CV-Library
        success = await scraper_service.authenticate_session(
            session_id,
            auth_request.username,
            auth_request.password
        )
        
        if success:
            # Get session data to return expiration info
            session_data = session_manager.get_session(session_id)
            
            return AuthResponse(
                success=True,
                message="Authentication successful",
                session_id=session_id,
                expires_at=session_data.expires_at if session_data else None
            )
        else:
            # Clean up failed session
            await session_manager.cleanup_session(session_id, force=True)
            raise HTTPException(status_code=401, detail="Invalid CV-Library credentials")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication service error")


@router.get("/status/{session_id}/")
async def get_auth_status(session_id: str, request: Request):
    """Get authentication status for a session."""
    session_manager = request.app.state.session_manager
    session_data = session_manager.get_session(session_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return AuthResponse(
        success=True,
        message="authenticated" if session_data.is_authenticated else "unauthenticated",
        session_id=session_id,
        expires_at=session_data.expires_at
    )


@router.post("/logout/{session_id}/")
async def logout(session_id: str, request: Request):
    """Logout and cleanup session."""
    try:
        session_manager = request.app.state.session_manager
        
        # Clean up the session
        cleanup_success = await session_manager.cleanup_session(session_id, force=True)
        
        return LogoutResponse(
            success=cleanup_success,
            message="Logout successful" if cleanup_success else "Session cleanup failed"
        )
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(status_code=500, detail="Logout service error")


@router.post("/extend/{session_id}/")
async def extend_session(session_id: str, request: Request):
    """Extend session expiration time."""
    try:
        session_manager = request.app.state.session_manager
        session_data = session_manager.get_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Extend session by updating last activity
        session_manager.update_session(session_id, last_activity=True)
        
        # Get updated session data
        updated_session = session_manager.get_session(session_id)
        
        return AuthResponse(
            success=True,
            message="Session extended successfully",
            session_id=session_id,
            expires_at=updated_session.expires_at if updated_session else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session extension failed: {e}")
        raise HTTPException(status_code=500, detail="Session extension service error") 