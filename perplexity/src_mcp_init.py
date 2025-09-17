"""MCP (Model Context Protocol) Management Module.

This module provides comprehensive MCP server management capabilities for the Telegram bot,
including server configuration, context handling, and Claude CLI integration.

Components:
- MCPManager: Core server management
- MCPContextHandler: Context selection and query execution  
- ServerConfigRegistry: Predefined server templates
- Exception handling and validation
"""

from .context_handler import MCPContextHandler
from .exceptions import (
    MCPContextError,
    MCPError,
    MCPServerNotFoundError,
    MCPValidationError,
)
from .manager import MCPManager, MCPServerConfig, MCPServerStatus
from .server_configs import server_config_registry

__all__ = [
    "MCPManager",
    "MCPContextHandler", 
    "MCPServerConfig",
    "MCPServerStatus",
    "server_config_registry",
    "MCPError",
    "MCPValidationError",
    "MCPServerNotFoundError", 
    "MCPContextError",
]
