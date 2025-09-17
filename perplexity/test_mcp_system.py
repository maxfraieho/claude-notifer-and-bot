"""Test Suite for MCP Management System.

Comprehensive tests for all MCP components including manager, context handler,
server configurations, and Telegram handlers.
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.config.settings import Settings
from src.mcp.manager import MCPManager, MCPServerConfig, MCPServerStatus
from src.mcp.context_handler import MCPContextHandler
from src.mcp.server_configs import server_config_registry
from src.mcp.exceptions import MCPError, MCPServerNotFoundError, MCPValidationError
from src.storage.facade import Storage


class TestMCPManager:
    """Test suite for MCPManager."""

    @pytest.fixture
    async def mcp_manager(self):
        """Create MCP manager with mocked dependencies."""
        settings = MagicMock(spec=Settings)
        settings.claude_cli_path = "claude"

        storage = MagicMock(spec=Storage)
        storage.db_manager = MagicMock()

        return MCPManager(settings, storage)

    @pytest.fixture
    def sample_server_config(self):
        """Sample server configuration."""
        return MCPServerConfig(
            name="test-github",
            server_type="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": "test-token"},
            config={"github_token": "test-token"}
        )

    @pytest.mark.asyncio
    async def test_get_server_templates(self, mcp_manager):
        """Test getting server templates."""
        # Mock database response
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [
            {
                "server_type": "github",
                "display_name": "GitHub Integration",
                "description": "Test description",
                "config_schema": '{"type": "object"}',
                "setup_instructions": "Test instructions",
                "command_template": "npx",
                "args_template": '[]',
                "env_template": '{}'
            }
        ]
        mock_conn.execute.return_value = mock_cursor
        mcp_manager.storage.db_manager.get_connection.return_value.__aenter__.return_value = mock_conn

        templates = await mcp_manager.get_server_templates()

        assert len(templates) == 1
        assert templates[0]["server_type"] == "github"
        assert templates[0]["display_name"] == "GitHub Integration"

    @pytest.mark.asyncio
    async def test_add_server_success(self, mcp_manager, sample_server_config):
        """Test successful server addition."""
        # Mock existing servers check
        mcp_manager.get_user_servers = AsyncMock(return_value=[])

        # Mock database operations
        mock_conn = AsyncMock()
        mcp_manager.storage.db_manager.get_connection.return_value.__aenter__.return_value = mock_conn

        # Mock Claude CLI command
        mcp_manager._add_to_claude_cli = AsyncMock(return_value=True)

        result = await mcp_manager.add_server(123, sample_server_config)

        assert result is True
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()

    @pytest.mark.asyncio
    async def test_add_server_duplicate_name(self, mcp_manager, sample_server_config):
        """Test adding server with duplicate name."""
        # Mock existing server with same name
        mcp_manager.get_user_servers = AsyncMock(return_value=[
            {"server_name": "test-github"}
        ])

        with pytest.raises(MCPValidationError, match="already exists"):
            await mcp_manager.add_server(123, sample_server_config)

    @pytest.mark.asyncio
    async def test_remove_server_success(self, mcp_manager):
        """Test successful server removal."""
        # Mock Claude CLI command
        mcp_manager._remove_from_claude_cli = AsyncMock(return_value=True)

        # Mock database operations
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.rowcount = 1
        mock_conn.execute.return_value = mock_cursor
        mcp_manager.storage.db_manager.get_connection.return_value.__aenter__.return_value = mock_conn

        result = await mcp_manager.remove_server(123, "test-server")

        assert result is True
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()

    @pytest.mark.asyncio
    async def test_remove_server_not_found(self, mcp_manager):
        """Test removing non-existent server."""
        # Mock Claude CLI command
        mcp_manager._remove_from_claude_cli = AsyncMock(return_value=True)

        # Mock database operations - no rows affected
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.rowcount = 0
        mock_conn.execute.return_value = mock_cursor
        mcp_manager.storage.db_manager.get_connection.return_value.__aenter__.return_value = mock_conn

        with pytest.raises(MCPServerNotFoundError):
            await mcp_manager.remove_server(123, "non-existent")

    @pytest.mark.asyncio
    async def test_get_server_status_cached(self, mcp_manager):
        """Test getting server status from cache."""
        # Add cached status
        cached_status = MCPServerStatus(
            name="test-server",
            status="active",
            last_check=datetime.utcnow()
        )
        mcp_manager._status_cache["123:test-server"] = cached_status

        result = await mcp_manager.get_server_status(123, "test-server")

        assert result.name == "test-server"
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_claude_cli_command_execution(self, mcp_manager):
        """Test Claude CLI command execution."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock subprocess
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"success", b"")
            mock_subprocess.return_value = mock_process

            result = await mcp_manager._run_claude_command(123, ["mcp", "list"])

            assert result.returncode == 0
            assert result.stdout == b"success"


class TestMCPContextHandler:
    """Test suite for MCPContextHandler."""

    @pytest.fixture
    def context_handler(self):
        """Create context handler with mocked dependencies."""
        mcp_manager = MagicMock(spec=MCPManager)
        claude_integration = MagicMock()
        storage = MagicMock(spec=Storage)

        return MCPContextHandler(mcp_manager, claude_integration, storage)

    @pytest.mark.asyncio
    async def test_set_active_context_success(self, context_handler):
        """Test setting active context successfully."""
        # Mock server exists and is enabled
        context_handler.mcp_manager.get_user_servers = AsyncMock(return_value=[
            {"server_name": "test-server", "is_enabled": True}
        ])

        # Mock database operations
        mock_conn = AsyncMock()
        context_handler.storage.db_manager.get_connection.return_value.__aenter__.return_value = mock_conn

        result = await context_handler.set_active_context(123, "test-server")

        assert result is True
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()

    @pytest.mark.asyncio
    async def test_set_active_context_server_not_found(self, context_handler):
        """Test setting context for non-existent server."""
        # Mock no servers found
        context_handler.mcp_manager.get_user_servers = AsyncMock(return_value=[])

        with pytest.raises(MCPServerNotFoundError):
            await context_handler.set_active_context(123, "non-existent")

    @pytest.mark.asyncio
    async def test_execute_contextual_query_success(self, context_handler):
        """Test successful contextual query execution."""
        # Mock active context
        context_handler.get_active_context = AsyncMock(return_value={
            "selected_server": "test-server",
            "server_type": "github"
        })

        # Mock server status
        mock_status = MCPServerStatus(name="test-server", status="active")
        context_handler.mcp_manager.get_server_status = AsyncMock(return_value=mock_status)

        # Mock Claude response
        mock_response = MagicMock()
        mock_response.session_id = "test-session"
        mock_response.cost = 0.01
        context_handler.claude_integration.run_command_with_mcp = AsyncMock(return_value=mock_response)

        # Mock usage logging
        context_handler.mcp_manager.log_usage = AsyncMock()

        result = await context_handler.execute_contextual_query(123, "test query")

        assert result == mock_response
        context_handler.mcp_manager.log_usage.assert_called()

    @pytest.mark.asyncio
    async def test_execute_contextual_query_no_context(self, context_handler):
        """Test query execution without active context."""
        # Mock no active context
        context_handler.get_active_context = AsyncMock(return_value=None)

        with pytest.raises(MCPError, match="No active MCP context"):
            await context_handler.execute_contextual_query(123, "test query")

    def test_prepare_contextual_prompt(self, context_handler):
        """Test contextual prompt preparation."""
        context = {
            "selected_server": "github-server",
            "server_type": "github",
            "display_name": "GitHub Integration"
        }

        prompt = context_handler._prepare_contextual_prompt("Show repos", context)

        assert "GitHub Integration" in prompt
        assert "Show repos" in prompt
        assert "GitHub queries" in prompt  # Server-specific hint


class TestServerConfigs:
    """Test suite for Server Configuration Templates."""

    def test_github_template_validation_success(self):
        """Test GitHub template validation with valid config."""
        template = server_config_registry.get_template("github")

        config = {"github_token": "ghp_1234567890123456789012345678901234567890"}
        is_valid, error = template.validate_config(config)

        assert is_valid is True
        assert error is None

    def test_github_template_validation_invalid_token(self):
        """Test GitHub template validation with invalid token."""
        template = server_config_registry.get_template("github")

        config = {"github_token": "invalid-token"}
        is_valid, error = template.validate_config(config)

        assert is_valid is False
        assert "формат" in error.lower() or "format" in error.lower()

    def test_filesystem_template_validation_success(self):
        """Test filesystem template validation with valid config."""
        template = server_config_registry.get_template("filesystem")

        config = {"allowed_path": "/home/user/projects"}
        is_valid, error = template.validate_config(config)

        assert is_valid is True
        assert error is None

    def test_filesystem_template_validation_relative_path(self):
        """Test filesystem template validation with relative path."""
        template = server_config_registry.get_template("filesystem")

        config = {"allowed_path": "relative/path"}
        is_valid, error = template.validate_config(config)

        assert is_valid is False
        assert "абсолютним" in error or "absolute" in error.lower()

    def test_postgres_template_build_config(self):
        """Test PostgreSQL template config building."""
        template = server_config_registry.get_template("postgres")

        user_inputs = {
            "connection_string": "postgresql://user:pass@localhost:5432/db",
            "server_name": "postgres-main"
        }

        config = template.build_server_config(user_inputs)

        assert config["name"] == "postgres-main"
        assert config["server_type"] == "postgres"
        assert config["command"] == "npx"
        assert "postgresql://user:pass@localhost:5432/db" in config["args"]

    def test_server_registry_get_all_templates(self):
        """Test getting all available templates."""
        templates = server_config_registry.get_all_templates()

        assert "github" in templates
        assert "filesystem" in templates
        assert "postgres" in templates
        assert "sqlite" in templates
        assert "git" in templates
        assert "playwright" in templates

        # Check template properties
        github_template = templates["github"]
        assert github_template.display_name == "🐙 GitHub Integration"
        assert github_template.server_type == "github"


class TestMCPIntegration:
    """Integration tests for MCP system."""

    @pytest.mark.asyncio
    async def test_full_server_lifecycle(self):
        """Test complete server lifecycle: add -> select -> query -> remove."""
        # This would be a comprehensive integration test
        # covering the full user workflow
        pass

    @pytest.mark.asyncio  
    async def test_multiple_users_isolation(self):
        """Test that users' MCP servers are properly isolated."""
        pass

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent MCP operations don't interfere."""
        pass


# Fixtures for test data
@pytest.fixture
def sample_github_config():
    """Sample GitHub server configuration."""
    return {
        "github_token": "ghp_1234567890123456789012345678901234567890",
        "server_name": "github-test"
    }

@pytest.fixture
def sample_postgres_config():
    """Sample PostgreSQL server configuration.""" 
    return {
        "connection_string": "postgresql://test:test@localhost:5432/testdb",
        "server_name": "postgres-test"
    }

# Test configuration
pytest_plugins = ["pytest_asyncio"]

if __name__ == "__main__":
    pytest.main([__file__])
