from typing import Dict, Optional, List, Any
from src.sessions.postgres_session import PostgreSQLSession
import asyncio
import os

POSTGRES_DB_URL = os.getenv("POSTGRES_DB_URL", "postgresql://agentuser:secret123@localhost:5432/agents_db")

class SessionManager:
    """
    Manages conversation sessions with PostgreSQL-backed persistence.
    Supports:
    - Persistent sessions: PostgreSQL
    - Temporary sessions: In-memory fallback (not implemented here)
    """

    def __init__(self):
        self._sessions: Dict[str, PostgreSQLSession] = {}
        print("🐘 Session Manager initialized using PostgreSQL")

    def get_session(
        self, 
        user_id: str, 
        session_type: str = "persistent",
        conversation_id: Optional[str] = None
    ) -> PostgreSQLSession:
        session_key = f"{user_id}_{session_type}"
        if conversation_id:
            session_key += f"_{conversation_id}"

        if session_key in self._sessions:
            return self._sessions[session_key]

        if session_type == "persistent":
            session = PostgreSQLSession(session_key, POSTGRES_DB_URL)
            print(f"🐘 Created persistent PostgreSQL session: {session_key}")
        else:
            raise NotImplementedError("Temporary sessions are not supported with PostgreSQLSession")

        self._sessions[session_key] = session
        return session

    async def clear_session(
        self, 
        user_id: str, 
        session_type: str = "persistent",
        conversation_id: Optional[str] = None
    ) -> bool:
        session_key = f"{user_id}_{session_type}"
        if conversation_id:
            session_key += f"_{conversation_id}"

        if session_key in self._sessions:
            session = self._sessions[session_key]
            await session.clear_session()
            del self._sessions[session_key]
            print(f"🗑️ Cleared session: {session_key}")
            return True

        return False

    async def clear_all_user_sessions(self, user_id: str) -> int:
        cleared_count = 0
        sessions_to_clear = [k for k in self._sessions if k.startswith(f"{user_id}_")]

        for session_key in sessions_to_clear:
            session = self._sessions[session_key]
            await session.clear_session()
            del self._sessions[session_key]
            cleared_count += 1

        print(f"🗑️ Cleared {cleared_count} sessions for user {user_id}")
        return cleared_count

    async def get_session_summary(
        self, 
        user_id: str, 
        session_type: str = "persistent",
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        session = self.get_session(user_id, session_type, conversation_id)
        items = await session.get_items()

        user_messages = len([item for item in items if item.get("role") == "user"])
        assistant_messages = len([item for item in items if item.get("role") == "assistant"])

        return {
            "session_key": f"{user_id}_{session_type}" + (f"_{conversation_id}" if conversation_id else ""),
            "total_items": len(items),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "session_type": session_type,
            "has_conversation_data": len(items) > 0
        }

    def list_active_sessions(self) -> List[str]:
        return list(self._sessions.keys())

    async def export_session(
        self, 
        user_id: str, 
        session_type: str = "persistent",
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        session = self.get_session(user_id, session_type, conversation_id)
        return await session.get_items()

# Global session manager instance
session_manager = SessionManager()

# Utility functions for easy session management
async def get_user_session(user_id: str, persistent: bool = True) -> PostgreSQLSession:
    session_type = "persistent" if persistent else "temporary"
    return session_manager.get_session(user_id, session_type)

async def clear_user_session(user_id: str, persistent: bool = True) -> bool:
    session_type = "persistent" if persistent else "temporary"
    return await session_manager.clear_session(user_id, session_type)

__all__ = [
    'SessionManager',
    'session_manager',
    'get_user_session', 
    'clear_user_session'
]
