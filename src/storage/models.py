"""Data models for storage.

Using dataclasses for simplicity and type safety.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import aiosqlite


@dataclass
class UserModel:
    """User data model."""

    user_id: int
    telegram_username: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_active: Optional[datetime] = None
    is_allowed: bool = False
    total_cost: float = 0.0
    message_count: int = 0
    session_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ["first_seen", "last_active"]:
            if data[key]:
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "UserModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        for field in ["first_seen", "last_active"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)


@dataclass
class SessionModel:
    """Session data model."""

    session_id: str
    user_id: int
    project_path: str
    created_at: datetime
    last_used: datetime
    total_cost: float = 0.0
    total_turns: int = 0
    message_count: int = 0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ["created_at", "last_used"]:
            if data[key]:
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "SessionModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        for field in ["created_at", "last_used"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)

    def is_expired(self, timeout_hours: int) -> bool:
        """Check if session has expired."""
        if not self.last_used:
            return True

        age = datetime.utcnow() - self.last_used
        return age.total_seconds() > (timeout_hours * 3600)


@dataclass
class MessageModel:
    """Message data model."""

    session_id: str
    user_id: int
    timestamp: datetime
    prompt: str
    message_id: Optional[int] = None
    response: Optional[str] = None
    cost: float = 0.0
    duration_ms: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        if data["timestamp"]:
            data["timestamp"] = data["timestamp"].isoformat()
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "MessageModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)


@dataclass
class ToolUsageModel:
    """Tool usage data model."""

    session_id: str
    tool_name: str
    timestamp: datetime
    id: Optional[int] = None
    message_id: Optional[int] = None
    tool_input: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        if data["timestamp"]:
            data["timestamp"] = data["timestamp"].isoformat()
        # Convert tool_input to JSON string if present
        if data["tool_input"]:
            data["tool_input"] = json.dumps(data["tool_input"])
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "ToolUsageModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Parse JSON fields
        if data.get("tool_input"):
            try:
                data["tool_input"] = json.loads(data["tool_input"])
            except (json.JSONDecodeError, TypeError):
                data["tool_input"] = {}

        return cls(**data)


@dataclass
class AuditLogModel:
    """Audit log data model."""

    user_id: int
    event_type: str
    timestamp: datetime
    id: Optional[int] = None
    event_data: Optional[Dict[str, Any]] = None
    success: bool = True
    ip_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        if data["timestamp"]:
            data["timestamp"] = data["timestamp"].isoformat()
        # Convert event_data to JSON string if present
        if data["event_data"]:
            data["event_data"] = json.dumps(data["event_data"])
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "AuditLogModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Parse JSON fields
        if data.get("event_data"):
            try:
                data["event_data"] = json.loads(data["event_data"])
            except (json.JSONDecodeError, TypeError):
                data["event_data"] = {}

        return cls(**data)


@dataclass
class CostTrackingModel:
    """Cost tracking data model."""

    user_id: int
    date: str  # ISO date format (YYYY-MM-DD)
    daily_cost: float = 0.0
    request_count: int = 0
    id: Optional[int] = None

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "CostTrackingModel":
        """Create from database row."""
        return cls(**dict(row))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class UserTokenModel:
    """User token data model."""

    user_id: int
    token_hash: str
    created_at: datetime
    token_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ["created_at", "expires_at", "last_used"]:
            if data[key]:
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "UserTokenModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        for field in ["created_at", "expires_at", "last_used"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)

    def is_expired(self) -> bool:
        """Check if token has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class ScheduledTaskModel:
    """Scheduled task data model for automated execution."""

    user_id: int
    task_type: str
    prompt: str
    created_at: datetime
    task_id: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    auto_execute: bool = True
    auto_respond: bool = True
    status: str = "pending"  # pending, running, completed, failed, cancelled
    result: Optional[str] = None
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_duration_ms: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 1  # 1=high, 2=medium, 3=low
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ["created_at", "scheduled_for", "executed_at"]:
            if data[key]:
                data[key] = data[key].isoformat()
        # Convert metadata to JSON string if present
        if data["metadata"]:
            data["metadata"] = json.dumps(data["metadata"])
        return data

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "ScheduledTaskModel":
        """Create from database row."""
        data = dict(row)

        # Parse datetime fields
        for field in ["created_at", "scheduled_for", "executed_at"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        # Parse JSON fields
        if data.get("metadata"):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except (json.JSONDecodeError, TypeError):
                data["metadata"] = {}

        return cls(**data)

    def is_ready_for_execution(self) -> bool:
        """Check if task is ready for execution."""
        if self.status != "pending":
            return False

        if self.scheduled_for:
            return datetime.utcnow() >= self.scheduled_for

        return True

    def is_failed_with_retries(self) -> bool:
        """Check if task has failed and exhausted retries."""
        return self.status == "failed" and self.retry_count >= self.max_retries

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.status == "failed" and self.retry_count < self.max_retries

    def mark_running(self) -> None:
        """Mark task as running."""
        self.status = "running"

    def mark_completed(self, result: str, duration_ms: Optional[int] = None) -> None:
        """Mark task as completed."""
        self.status = "completed"
        self.result = result
        self.executed_at = datetime.utcnow()
        if duration_ms:
            self.execution_duration_ms = duration_ms

    def mark_failed(self, error: str) -> None:
        """Mark task as failed and increment retry count."""
        self.status = "failed"
        self.error_message = error
        self.retry_count += 1
        self.executed_at = datetime.utcnow()


__all__ = ["UserModel", "SessionModel", "ScheduledTaskModel"]
