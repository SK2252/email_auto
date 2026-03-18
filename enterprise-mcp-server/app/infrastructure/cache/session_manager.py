"""
Redis-backed session manager for the Enterprise MCP Server.
Handles CRUD operations for user sessions with automatic TTL management.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.core.config import settings
from app.infrastructure.cache.redis_client import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manages user sessions in Redis.
    
    Keys:
      - Session data: "mcp:session:{session_id}" (Hash or JSON string)
      - User sessions: "mcp:user_sessions:{user_id}" (Set of session_ids)
    """
    
    PREFIX = "mcp:session:"
    USER_PREFIX = "mcp:user_sessions:"

    async def create_session(
        self, 
        user_id: str, 
        agent_capabilities: Optional[Dict] = None
    ) -> Dict:
        """
        Create a new session for a user.
        
        Args:
            user_id: The unique identifier of the user (from API key owner).
            agent_capabilities: Dictionary of allowed agents and their tools.
        
        Returns:
            The complete session dictionary.
        """
        redis = await get_redis()
        if not redis:
            logger.warning("Redis unavailable — cannot create session")
            return {}

        session_id = str(uuid.uuid4())
        
        # Use IST (UTC+05:30) as requested
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        expires_at = now + timedelta(seconds=settings.session_ttl_seconds)

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "agent_capabilities": agent_capabilities or {},
            "conversation_context": [],  # Short-term memory
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "refresh_count": 0,
            "last_agent": None
        }

        # Transaction: Save session + add to user's list
        async with redis.pipeline(transaction=True) as pipe:
            # 1. Save session data (as JSON string for simplicity)
            await pipe.setex(
                f"{self.PREFIX}{session_id}",
                settings.session_ttl_seconds,
                json.dumps(session_data)
            )
            
            # 2. Add to user's session list
            await pipe.sadd(f"{self.USER_PREFIX}{user_id}", session_id)
            
            # 3. Set expiry on user list (cleanup if user is inactive)
            await pipe.expire(
                f"{self.USER_PREFIX}{user_id}", 
                settings.session_ttl_seconds + 3600
            )
            
            await pipe.execute()

        logger.info("Session created", session_id=session_id, user_id=user_id)
        return session_data

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve a session by ID."""
        redis = await get_redis()
        if not redis:
            return None

        data = await redis.get(f"{self.PREFIX}{session_id}")
        if not data:
            return None

        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error("Failed to decode session data", session_id=session_id)
            return None

    async def update_session(self, session_id: str, updates: Dict) -> bool:
        """
        Update specific fields in a session.
        Note: This is a read-modify-write operation (optimistic locking not implemented for MVP).
        """
        redis = await get_redis()
        if not redis:
            return False

        key = f"{self.PREFIX}{session_id}"
        
        # Get current data
        current_data_str = await redis.get(key)
        if not current_data_str:
            return False
            
        try:
            current_data = json.loads(current_data_str)
        except json.JSONDecodeError:
            return False

        # Apply updates
        current_data.update(updates)
        
        # Save back with existing TTL (don't reset TTL here unless requested)
        ttl = await redis.ttl(key)
        if ttl < 0:
            ttl = settings.session_ttl_seconds

        await redis.setex(key, ttl, json.dumps(current_data))
        return True

    async def refresh_ttl(self, session_id: str) -> bool:
        """Reset the session TTL to the configured duration."""
        redis = await get_redis()
        if not redis:
            return False

        return await redis.expire(
            f"{self.PREFIX}{session_id}", 
            settings.session_ttl_seconds
        )

    async def delete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a session and remove it from the user's list."""
        redis = await get_redis()
        if not redis:
            return False

        key = f"{self.PREFIX}{session_id}"
        
        # If user_id not provided, try to fetch it from session first
        if not user_id:
            data = await redis.get(key)
            if data:
                try:
                    session = json.loads(data)
                    user_id = session.get("user_id")
                except:
                    pass

        async with redis.pipeline(transaction=True) as pipe:
            await pipe.delete(key)
            if user_id:
                await pipe.srem(f"{self.USER_PREFIX}{user_id}", session_id)
            await pipe.execute()
            
        logger.info("Session deleted", session_id=session_id)
        return True

    async def list_user_sessions(self, user_id: str) -> List[str]:
        """List all active session IDs for a user."""
        redis = await get_redis()
        if not redis:
            return []

        members = await redis.smembers(f"{self.USER_PREFIX}{user_id}")
        return list(members)


# Singleton instance
session_manager = SessionManager()
