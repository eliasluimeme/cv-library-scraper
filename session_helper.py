#!/usr/bin/env python3
"""
Session Helper - Store and retrieve session IDs for the CV-Library Scraper API

This script helps you manage session IDs so you can reuse authenticated sessions
without having to re-authenticate every time.
"""

import json
import os
from datetime import datetime
from typing import Optional

SESSION_FILE = ".api_sessions.json"


def save_session(session_id: str, username: str, expires_at: str = None):
    """Save a session ID for later use."""
    sessions = load_sessions()
    
    sessions[username] = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at,
        "last_used": datetime.now().isoformat()
    }
    
    with open(SESSION_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)
    
    print(f"✅ Session saved for {username}: {session_id}")


def get_session(username: str) -> Optional[str]:
    """Get the most recent session ID for a user."""
    sessions = load_sessions()
    
    if username in sessions:
        session_info = sessions[username]
        session_id = session_info["session_id"]
        
        # Update last used time
        session_info["last_used"] = datetime.now().isoformat()
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
        
        print(f"📋 Retrieved session for {username}: {session_id}")
        return session_id
    
    print(f"❌ No session found for {username}")
    return None


def load_sessions() -> dict:
    """Load sessions from file."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def list_sessions():
    """List all stored sessions."""
    sessions = load_sessions()
    
    if not sessions:
        print("📭 No sessions stored")
        return
    
    print("📋 Stored Sessions:")
    print("-" * 60)
    for username, info in sessions.items():
        print(f"User: {username}")
        print(f"  Session ID: {info['session_id']}")
        print(f"  Created: {info['created_at']}")
        print(f"  Last Used: {info['last_used']}")
        if info.get('expires_at'):
            print(f"  Expires: {info['expires_at']}")
        print()


def clear_sessions():
    """Clear all stored sessions."""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    print("🗑️ All sessions cleared")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python session_helper.py save <session_id> <username> [expires_at]")
        print("  python session_helper.py get <username>")
        print("  python session_helper.py list")
        print("  python session_helper.py clear")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "save" and len(sys.argv) >= 4:
        session_id = sys.argv[2]
        username = sys.argv[3]
        expires_at = sys.argv[4] if len(sys.argv) > 4 else None
        save_session(session_id, username, expires_at)
    
    elif command == "get" and len(sys.argv) >= 3:
        username = sys.argv[2]
        session_id = get_session(username)
        if session_id:
            print(f"Session ID: {session_id}")
    
    elif command == "list":
        list_sessions()
    
    elif command == "clear":
        clear_sessions()
    
    else:
        print("Invalid command or missing arguments")
        sys.exit(1) 