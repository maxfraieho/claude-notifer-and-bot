"""User language preference storage."""

import asyncio
from typing import Dict, Optional

import structlog

from ..storage.facade import Storage

logger = structlog.get_logger()


class UserLanguageStorage:
    """Manages user language preferences."""

    def __init__(self, storage: Storage):
        """Initialize with storage facade."""
        self.storage = storage
        self._cache: Dict[int, str] = {}

    async def get_user_language(self, user_id: int) -> Optional[str]:
        """Get user's preferred language.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Language code or None if not set
        """
        # Check cache first
        if user_id in self._cache:
            return self._cache[user_id]

        # Try to get from database
        try:
            language = await self._get_from_database(user_id)
            if language:
                self._cache[user_id] = language
            return language
        except Exception as e:
            logger.error("Failed to get user language", user_id=user_id, error=str(e))
            return None

    async def set_user_language(self, user_id: int, language: str) -> bool:
        """Set user's preferred language.
        
        Args:
            user_id: Telegram user ID
            language: Language code to set
            
        Returns:
            True if successfully set
        """
        try:
            success = await self._set_in_database(user_id, language)
            if success:
                self._cache[user_id] = language
            return success
        except Exception as e:
            logger.error("Failed to set user language", user_id=user_id, language=language, error=str(e))
            return False

    async def _get_from_database(self, user_id: int) -> Optional[str]:
        """Get language from database."""
        # For now, use a simple approach with database queries
        # This can be expanded to use the existing storage system
        async with self.storage.db_manager.get_connection() as connection:
            try:
                cursor = await connection.execute(
                    "SELECT language FROM user_languages WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                return row[0] if row else None
            except Exception:
                # If table doesn't exist, create it
                await self._create_table_if_not_exists(connection)
                return None

    async def _set_in_database(self, user_id: int, language: str) -> bool:
        """Set language in database."""
        async with self.storage.db_manager.get_connection() as connection:
            try:
                await self._create_table_if_not_exists(connection)
                await connection.execute(
                    "INSERT OR REPLACE INTO user_languages (user_id, language) VALUES (?, ?)",
                    (user_id, language)
                )
                await connection.commit()
                return True
            except Exception as e:
                logger.error("Database error", error=str(e))
                return False

    async def _create_table_if_not_exists(self, connection) -> None:
        """Create user_languages table if it doesn't exist."""
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS user_languages (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)