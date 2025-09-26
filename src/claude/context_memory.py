"""Context memory management for persistent conversation context across sessions.

This module provides long-term context memory that survives session boundaries,
allowing Claude CLI to maintain awareness of previous conversations through the bot.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import structlog

from ..storage.facade import Storage
from ..storage.models import MessageModel, SessionModel, ContextEntryModel

logger = structlog.get_logger()


@dataclass
class ContextEntry:
    """Single context entry with metadata."""

    content: str
    timestamp: datetime
    session_id: str
    message_type: str  # "user", "assistant", "system", "summary"
    importance: int = 1  # 1=high, 2=medium, 3=low
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "message_type": self.message_type,
            "importance": self.importance,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        """Create from dictionary."""
        return cls(
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            session_id=data["session_id"],
            message_type=data["message_type"],
            importance=data.get("importance", 1),
            metadata=data.get("metadata", {}),
        )


@dataclass
class UserContext:
    """User's persistent context across sessions."""

    user_id: int
    project_path: str
    entries: List[ContextEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    max_entries: int = 100  # Maximum context entries to keep
    max_tokens: int = 50000  # Approximate token limit for context

    def add_entry(self, entry: ContextEntry) -> None:
        """Add new context entry."""
        self.entries.append(entry)
        self.last_updated = datetime.utcnow()
        self._cleanup_if_needed()

    def _cleanup_if_needed(self) -> None:
        """Clean up old entries if limits exceeded."""
        # Sort by importance and timestamp (most important and recent first)
        self.entries.sort(key=lambda e: (e.importance, -e.timestamp.timestamp()))

        # Keep only max_entries
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[:self.max_entries]
            logger.info("Context entries cleaned up",
                       user_id=self.user_id,
                       kept=len(self.entries))

    def get_recent_context(self, max_entries: int = 20) -> List[ContextEntry]:
        """Get most recent context entries."""
        return sorted(self.entries, key=lambda e: e.timestamp, reverse=True)[:max_entries]

    def get_relevant_context(self, query: str = "", max_entries: int = 10) -> List[ContextEntry]:
        """Get context entries relevant to the query."""
        # Simple relevance scoring - can be enhanced with embedding similarity
        if not query:
            return self.get_recent_context(max_entries)

        query_lower = query.lower()
        scored_entries = []

        for entry in self.entries:
            score = 0
            content_lower = entry.content.lower()

            # Basic keyword matching
            for word in query_lower.split():
                if word in content_lower:
                    score += 1

            # Boost importance and recency
            importance_boost = (4 - entry.importance) * 0.5  # Higher importance = higher score
            recency_boost = max(0, 1 - (datetime.utcnow() - entry.timestamp).days / 30)  # Recent = higher score

            final_score = score + importance_boost + recency_boost
            scored_entries.append((entry, final_score))

        # Sort by score and return top entries
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, score in scored_entries[:max_entries] if score > 0]

    def to_claude_context(self, max_entries: int = 15) -> str:
        """Generate context string for Claude CLI."""
        relevant_entries = self.get_recent_context(max_entries)

        if not relevant_entries:
            return ""

        context_lines = [
            "# Previous conversation context",
            f"# Project: {self.project_path}",
            f"# Last updated: {self.last_updated.strftime('%Y-%m-%d %H:%M')}",
            ""
        ]

        for entry in relevant_entries:
            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M')
            context_lines.append(f"## [{timestamp}] {entry.message_type.title()}")
            context_lines.append(entry.content)
            context_lines.append("")

        return "\n".join(context_lines)


class ContextMemoryManager:
    """Manages persistent context memory across Claude sessions."""

    def __init__(self, storage: Storage):
        """Initialize context memory manager.

        Args:
            storage: Storage facade for persistence
        """
        self.storage = storage
        self._user_contexts: Dict[str, UserContext] = {}  # key: f"{user_id}:{project_path}"

    def _get_context_key(self, user_id: int, project_path: str) -> str:
        """Generate unique key for user context."""
        return f"{user_id}:{project_path}"

    async def get_user_context(self, user_id: int, project_path: str) -> UserContext:
        """Get or create user context."""
        context_key = self._get_context_key(user_id, project_path)

        if context_key not in self._user_contexts:
            # Try to load from storage first
            context = await self._load_context_from_storage(user_id, project_path)
            if not context:
                # Create new context
                context = UserContext(user_id=user_id, project_path=project_path)
                logger.info("Created new user context",
                           user_id=user_id,
                           project_path=project_path)

            self._user_contexts[context_key] = context

        return self._user_contexts[context_key]

    async def add_message_to_context(
        self,
        user_id: int,
        project_path: str,
        session_id: str,
        content: str,
        message_type: str,
        importance: int = 2
    ) -> None:
        """Add message to user's context."""
        logger.info("Adding message to context",
                   user_id=user_id,
                   project_path=project_path,
                   session_id=session_id,
                   message_type=message_type)

        context = await self.get_user_context(user_id, project_path)

        entry = ContextEntry(
            content=content,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            message_type=message_type,
            importance=importance,
            metadata={"project_path": project_path}
        )

        context.add_entry(entry)
        logger.info("Context entry added, now saving to storage", user_id=user_id)
        await self._save_context_to_storage(context)
        logger.info("Context saved to storage successfully", user_id=user_id)

        logger.debug("Added message to context",
                    user_id=user_id,
                    session_id=session_id,
                    message_type=message_type)

    async def get_context_for_claude(
        self,
        user_id: int,
        project_path: str,
        query: str = "",
        max_entries: int = 15
    ) -> str:
        """Get formatted context for Claude CLI."""
        context = await self.get_user_context(user_id, project_path)

        if query:
            relevant_entries = context.get_relevant_context(query, max_entries)
        else:
            relevant_entries = context.get_recent_context(max_entries)

        if not relevant_entries:
            return ""

        # Generate context string
        context_lines = [
            "# Previous conversation context from Telegram bot",
            f"# Project: {project_path}",
            f"# Last updated: {context.last_updated.strftime('%Y-%m-%d %H:%M')}",
            "# This context helps maintain continuity across Claude CLI sessions",
            ""
        ]

        for entry in relevant_entries:
            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M')
            context_lines.append(f"## [{timestamp}] {entry.message_type.title()}")
            context_lines.append(entry.content.strip())
            context_lines.append("")

        context_lines.append("---")
        context_lines.append("# End of previous context. Continue the conversation:")
        context_lines.append("")

        return "\n".join(context_lines)

    async def import_session_messages(
        self,
        user_id: int,
        project_path: str,
        session_id: str
    ) -> int:
        """Import messages from existing session into context."""
        try:
            # Get session messages from storage
            messages = await self.storage.message.get_session_messages(session_id)

            imported_count = 0
            context = await self.get_user_context(user_id, project_path)

            for message in messages:
                # Add user prompt
                if message.prompt:
                    entry = ContextEntry(
                        content=message.prompt,
                        timestamp=message.timestamp,
                        session_id=session_id,
                        message_type="user",
                        importance=2
                    )
                    context.add_entry(entry)
                    imported_count += 1

                # Add Claude response
                if message.response:
                    entry = ContextEntry(
                        content=message.response,
                        timestamp=message.timestamp,
                        session_id=session_id,
                        message_type="assistant",
                        importance=2
                    )
                    context.add_entry(entry)
                    imported_count += 1

            if imported_count > 0:
                await self._save_context_to_storage(context)
                logger.info("Imported session messages to context",
                           session_id=session_id,
                           imported_count=imported_count)

            return imported_count

        except Exception as e:
            logger.error("Failed to import session messages",
                        session_id=session_id,
                        error=str(e))
            return 0

    async def export_context(self, user_id: int, project_path: str) -> Dict[str, Any]:
        """Export user context for backup/transfer."""
        context = await self.get_user_context(user_id, project_path)

        return {
            "user_id": context.user_id,
            "project_path": context.project_path,
            "created_at": context.created_at.isoformat(),
            "last_updated": context.last_updated.isoformat(),
            "entries": [entry.to_dict() for entry in context.entries],
            "max_entries": context.max_entries,
            "max_tokens": context.max_tokens,
        }

    async def import_context(self, context_data: Dict[str, Any]) -> bool:
        """Import context from exported data."""
        try:
            user_id = context_data["user_id"]
            project_path = context_data["project_path"]

            context = UserContext(
                user_id=user_id,
                project_path=project_path,
                created_at=datetime.fromisoformat(context_data["created_at"]),
                last_updated=datetime.fromisoformat(context_data["last_updated"]),
                max_entries=context_data.get("max_entries", 100),
                max_tokens=context_data.get("max_tokens", 50000),
            )

            # Import entries
            for entry_data in context_data["entries"]:
                entry = ContextEntry.from_dict(entry_data)
                context.add_entry(entry)

            # Save to storage
            context_key = self._get_context_key(user_id, project_path)
            self._user_contexts[context_key] = context
            await self._save_context_to_storage(context)

            logger.info("Context imported successfully",
                       user_id=user_id,
                       project_path=project_path,
                       entries_count=len(context.entries))

            return True

        except Exception as e:
            logger.error("Failed to import context", error=str(e))
            return False

    async def clear_context(self, user_id: int, project_path: str) -> bool:
        """Clear user's context."""
        try:
            context_key = self._get_context_key(user_id, project_path)

            # Remove from memory
            if context_key in self._user_contexts:
                del self._user_contexts[context_key]

            # Remove from storage (if implemented)
            # TODO: Add storage deletion when context storage is implemented

            logger.info("Context cleared", user_id=user_id, project_path=project_path)
            return True

        except Exception as e:
            logger.error("Failed to clear context",
                        user_id=user_id,
                        project_path=project_path,
                        error=str(e))
            return False

    async def _load_context_from_storage(
        self,
        user_id: int,
        project_path: str
    ) -> Optional[UserContext]:
        """Load context from persistent storage."""
        try:
            # Try to load from context entries table first
            context_entries = await self.storage.context.get_user_context_entries(
                user_id=user_id,
                project_path=project_path,
                limit=100
            )

            if context_entries:
                # Create context from stored entries
                context = UserContext(user_id=user_id, project_path=project_path)

                for entry_model in context_entries:
                    entry = ContextEntry(
                        content=entry_model.content,
                        timestamp=entry_model.timestamp,
                        session_id=entry_model.session_id,
                        message_type=entry_model.message_type,
                        importance=entry_model.importance,
                        metadata=entry_model.metadata or {}
                    )
                    # Mark as saved to avoid re-saving
                    entry._saved = True
                    context.entries.append(entry)

                # Update last_updated time
                if context.entries:
                    context.last_updated = max(e.timestamp for e in context.entries)

                logger.info("Context loaded from database",
                           user_id=user_id,
                           project_path=project_path,
                           entries_count=len(context.entries))
                return context

            # Fallback: reconstruct from recent sessions
            sessions = await self.storage.sessions.get_user_sessions(user_id)
            project_sessions = [s for s in sessions if s.project_path == project_path]

            if not project_sessions:
                return None

            # Create context and import from most recent sessions
            context = UserContext(user_id=user_id, project_path=project_path)

            # Import messages from last few sessions
            for session in project_sessions[-5:]:  # Last 5 sessions
                await self._import_session_to_context(context, session.session_id)

            if context.entries:
                logger.info("Context reconstructed from sessions",
                           user_id=user_id,
                           project_path=project_path,
                           entries_count=len(context.entries))
                return context

        except Exception as e:
            logger.error("Failed to load context from storage",
                        user_id=user_id,
                        project_path=project_path,
                        error=str(e))

        return None

    async def _import_session_to_context(
        self,
        context: UserContext,
        session_id: str
    ) -> None:
        """Import messages from session to context."""
        try:
            messages = await self.storage.messages.get_session_messages(session_id)

            for message in messages[-10:]:  # Last 10 messages per session
                # Add user prompt
                if message.prompt:
                    entry = ContextEntry(
                        content=message.prompt,
                        timestamp=message.timestamp,
                        session_id=session_id,
                        message_type="user",
                        importance=3  # Lower importance for auto-imported
                    )
                    context.add_entry(entry)

                # Add Claude response (summarized if too long)
                if message.response:
                    response_content = message.response
                    if len(response_content) > 500:
                        response_content = response_content[:500] + "... [truncated]"

                    entry = ContextEntry(
                        content=response_content,
                        timestamp=message.timestamp,
                        session_id=session_id,
                        message_type="assistant",
                        importance=3  # Lower importance for auto-imported
                    )
                    context.add_entry(entry)

        except Exception as e:
            logger.error("Failed to import session to context",
                        session_id=session_id,
                        error=str(e))

    async def _save_context_to_storage(self, context: UserContext) -> None:
        """Save context to persistent storage."""
        try:
            logger.info("Starting context save to storage",
                       user_id=context.user_id,
                       entries_count=len(context.entries))

            # Save context entries to database
            saved_count = 0
            for entry in context.entries:
                if not hasattr(entry, '_saved'):
                    logger.info("Saving context entry",
                               user_id=context.user_id,
                               message_type=entry.message_type,
                               content_length=len(entry.content))

                    # Create ContextEntryModel and save
                    context_entry_model = ContextEntryModel(
                        user_id=context.user_id,
                        project_path=context.project_path,
                        content=entry.content,
                        timestamp=entry.timestamp,
                        session_id=entry.session_id,
                        message_type=entry.message_type,
                        importance=entry.importance,
                        metadata=entry.metadata
                    )

                    saved_entry = await self.storage.context.save_context_entry(context_entry_model)
                    # Mark as saved to avoid duplicates
                    entry._saved = True
                    saved_count += 1

            logger.info("Context saved to storage successfully",
                       user_id=context.user_id,
                       saved_entries=saved_count)

            logger.debug("Context saved to storage",
                        user_id=context.user_id,
                        project_path=context.project_path,
                        entries_count=len(context.entries))

        except Exception as e:
            logger.error("Failed to save context to storage",
                        user_id=context.user_id,
                        project_path=context.project_path,
                        error=str(e))