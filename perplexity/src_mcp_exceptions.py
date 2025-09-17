"""MCP-specific exceptions for error handling."""

from ..exceptions import ClaudeCodeTelegramError


class MCPError(ClaudeCodeTelegramError):
    """Base MCP-related error."""
    pass


class MCPValidationError(MCPError):
    """MCP validation error."""
    pass


class MCPServerNotFoundError(MCPError):
    """MCP server not found error."""
    pass


class MCPContextError(MCPError):
    """MCP context-related error."""
    pass


class MCPConnectionError(MCPError):
    """MCP connection error."""
    pass


class MCPCommandError(MCPError):
    """MCP command execution error."""
    pass


class MCPConfigurationError(MCPError):
    """MCP configuration error."""
    pass
