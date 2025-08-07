"""
Session management service for handling browser sessions and state.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
import threading
import weakref
import hashlib
import re

from api.core.config import get_settings


@dataclass
class SessionData:
    """Session data container."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: Optional[datetime]
    scraper_instance: Optional[Any] = None
    is_authenticated: bool = False
    active_scrapes: Dict[str, Any] = field(default_factory=dict)
    total_downloads: int = 0
    total_scrapes: int = 0
    user_info: Optional[Dict[str, Any]] = None
    username: Optional[str] = None  # Add username for profile generation
    browser_profile_name: Optional[str] = None  # Store the generated profile name
    status: str = "active"
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session data to dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_authenticated": self.is_authenticated,
            "active_scrapes": len(self.active_scrapes),
            "total_downloads": self.total_downloads,
            "total_scrapes": self.total_scrapes,
            "username": self.username,
            "browser_profile_name": self.browser_profile_name,
            "status": self.status
        }


class SessionManager:
    """Manages browser sessions and their lifecycle."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Session storage
        self._sessions: Dict[str, SessionData] = {}
        self._session_lock = threading.RLock()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Metrics
        self.total_sessions_created = 0
        self.total_sessions_expired = 0
        
        self.logger.info("SessionManager initialized")
    
    async def start_cleanup_task(self):
        """Start the session cleanup background task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("Session cleanup task started")
    
    async def _cleanup_loop(self):
        """Background task to cleanup expired sessions."""
        while not self._shutdown_event.is_set():
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        with self._session_lock:
            expired_sessions = []
            
            for session_id, session_data in self._sessions.items():
                if session_data.is_expired() or session_data.status == "inactive":
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                try:
                    await self._cleanup_session(session_id)
                    self.total_sessions_expired += 1
                    self.logger.info(f"Cleaned up expired session: {session_id}")
                except Exception as e:
                    self.logger.error(f"Error cleaning up session {session_id}: {e}")
    
    def _generate_safe_profile_name(self, username: str) -> str:
        """Generate a safe browser profile name from username."""
        # Remove non-alphanumeric characters and convert to lowercase
        safe_username = re.sub(r'[^a-zA-Z0-9]', '_', username.lower())
        
        # Limit length and add hash for uniqueness
        if len(safe_username) > 20:
            # Use first 15 chars + 5 char hash for very long usernames
            username_hash = hashlib.md5(username.encode()).hexdigest()[:5]
            safe_username = safe_username[:15] + "_" + username_hash
        
        return f"user_{safe_username}"
    
    def create_session(self, remember_session: bool = True, username: Optional[str] = None) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        expires_at = None
        if remember_session:
            expires_at = now + timedelta(minutes=self.settings.session_timeout_minutes)
        
        # Generate user-specific browser profile name
        browser_profile_name = None
        if username:
            browser_profile_name = self._generate_safe_profile_name(username)
            self.logger.info(f"Generated browser profile name: {browser_profile_name} for user: {username}")
        
        session_data = SessionData(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            username=username,
            browser_profile_name=browser_profile_name
        )
        
        with self._session_lock:
            self._sessions[session_id] = session_data
            self.total_sessions_created += 1
        
        self.logger.info(f"Created session: {session_id} for user: {username or 'anonymous'}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data by ID."""
        with self._session_lock:
            session_data = self._sessions.get(session_id)
            
            if session_data and not session_data.is_expired():
                session_data.update_activity()
                return session_data
            elif session_data and session_data.is_expired():
                # Mark for cleanup
                session_data.status = "expired"
        
        return None
    
    def update_session(self, session_id: str, **updates) -> bool:
        """Update session data."""
        with self._session_lock:
            session_data = self._sessions.get(session_id)
            
            if session_data and not session_data.is_expired():
                for key, value in updates.items():
                    if hasattr(session_data, key):
                        setattr(session_data, key, value)
                
                session_data.update_activity()
                return True
        
        return False
    
    async def cleanup_session(self, session_id: str, force: bool = False) -> bool:
        """Clean up a specific session."""
        with self._session_lock:
            if session_id not in self._sessions:
                return False
            
            session_data = self._sessions[session_id]
            
            # Check if session has active operations
            if not force and session_data.active_scrapes:
                self.logger.warning(f"Cannot cleanup session {session_id}: has active scrape operations")
                return False
        
        try:
            await self._cleanup_session(session_id)
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up session {session_id}: {e}")
            return False
    
    async def _cleanup_session(self, session_id: str):
        """Internal session cleanup logic."""
        with self._session_lock:
            session_data = self._sessions.get(session_id)
            
            if session_data:
                # Cleanup scraper instance
                if session_data.scraper_instance:
                    try:
                        # Call cleanup method if available
                        if hasattr(session_data.scraper_instance, 'close'):
                            session_data.scraper_instance.close()
                    except Exception as e:
                        self.logger.error(f"Error closing scraper instance: {e}")
                
                # Remove from sessions
                del self._sessions[session_id]
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        with self._session_lock:
            sessions = []
            for session_data in self._sessions.values():
                if not session_data.is_expired():
                    sessions.append(session_data.to_dict())
            return sessions
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        with self._session_lock:
            active_sessions = sum(1 for s in self._sessions.values() if not s.is_expired())
            
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active_sessions,
                "total_created": self.total_sessions_created,
                "total_expired": self.total_sessions_expired,
                "max_concurrent": self.settings.max_concurrent_sessions
            }
    
    async def cleanup_all_sessions(self):
        """Clean up all sessions."""
        with self._session_lock:
            session_ids = list(self._sessions.keys())
        
        for session_id in session_ids:
            try:
                await self._cleanup_session(session_id)
            except Exception as e:
                self.logger.error(f"Error cleaning up session {session_id}: {e}")
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self._shutdown_event.set()
        self.logger.info("All sessions cleaned up") 