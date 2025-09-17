"""MCP Server Management System.

Core component for managing Model Context Protocol servers in the Telegram bot.
Handles server configuration, status monitoring, and Claude CLI integration.
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog
from pydantic import BaseModel, Field

from ..config.settings import Settings
from ..storage.facade import Storage
from .exceptions import MCPError, MCPServerNotFoundError, MCPValidationError

logger = structlog.get_logger()


class MCPServerConfig(BaseModel):
    """MCP server configuration model."""

    name: str
    server_type: str
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class MCPServerStatus(BaseModel):
    """MCP server status model."""

    name: str
    status: str  # inactive, active, error, connecting
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    response_time: Optional[int] = None


class MCPManager:
    """Main MCP server management class."""

    def __init__(self, settings: Settings, storage: Storage):
        """Initialize MCP manager."""
        self.settings = settings
        self.storage = storage
        self.claude_cli_path = settings.claude_cli_path or "claude"
        self._status_cache: Dict[str, MCPServerStatus] = {}
        self._cache_timeout = 300  # 5 minutes

    async def get_server_templates(self) -> List[Dict[str, Any]]:
        """Get available MCP server templates."""
        try:
            async with self.storage.db_manager.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT server_type, display_name, description, config_schema, 
                           setup_instructions, command_template, args_template, env_template
                    FROM mcp_server_templates 
                    WHERE is_active = true
                    ORDER BY display_name
                """)
                rows = await cursor.fetchall()

                templates = []
                for row in rows:
                    template = dict(row)
                    # Parse JSON fields
                    for field in ['config_schema', 'args_template', 'env_template']:
                        if template[field]:
                            template[field] = json.loads(template[field])
                    templates.append(template)

                return templates

        except Exception as e:
            logger.error("Failed to get server templates", error=str(e))
            return []

    async def get_user_servers(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's MCP servers."""
        try:
            async with self.storage.db_manager.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT s.*, t.display_name, t.description
                    FROM user_mcp_servers s
                    LEFT JOIN mcp_server_templates t ON s.server_type = t.server_type
                    WHERE s.user_id = %s
                    ORDER BY s.server_name
                """, (user_id,))
                rows = await cursor.fetchall()

                servers = []
                for row in rows:
                    server = dict(row)
                    # Parse JSON fields
                    for field in ['server_args', 'server_env', 'config']:
                        if server[field]:
                            server[field] = json.loads(server[field])
                    servers.append(server)

                return servers

        except Exception as e:
            logger.error("Failed to get user servers", user_id=user_id, error=str(e))
            return []

    async def add_server(self, user_id: int, config: MCPServerConfig) -> bool:
        """Add a new MCP server for user."""
        try:
            # Validate server name uniqueness
            existing_servers = await self.get_user_servers(user_id)
            if any(s['server_name'] == config.name for s in existing_servers):
                raise MCPValidationError(f"Server '{config.name}' already exists")

            # Insert server into database
            async with self.storage.db_manager.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO user_mcp_servers 
                    (user_id, server_name, server_type, server_command, server_args, 
                     server_env, config, is_enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    config.name,
                    config.server_type,
                    config.command,
                    json.dumps(config.args),
                    json.dumps(config.env),
                    json.dumps(config.config),
                    config.is_enabled
                ))
                await conn.commit()

            # Add server to Claude CLI
            if config.is_enabled:
                success = await self._add_to_claude_cli(user_id, config)
                if not success:
                    logger.warning("Server added to database but failed to add to Claude CLI", 
                                 server_name=config.name)

            logger.info("MCP server added successfully", 
                       user_id=user_id, server_name=config.name)
            return True

        except Exception as e:
            logger.error("Failed to add MCP server", 
                        user_id=user_id, server_name=config.name, error=str(e))
            raise MCPError(f"Failed to add server: {str(e)}")

    async def remove_server(self, user_id: int, server_name: str) -> bool:
        """Remove an MCP server."""
        try:
            # Remove from Claude CLI first
            await self._remove_from_claude_cli(user_id, server_name)

            # Remove from database
            async with self.storage.db_manager.get_connection() as conn:
                cursor = await conn.execute("""
                    DELETE FROM user_mcp_servers 
                    WHERE user_id = %s AND server_name = %s
                """, (user_id, server_name))

                if cursor.rowcount == 0:
                    raise MCPServerNotFoundError(f"Server '{server_name}' not found")

                await conn.commit()

            # Clear cache
            cache_key = f"{user_id}:{server_name}"
            self._status_cache.pop(cache_key, None)

            logger.info("MCP server removed successfully", 
                       user_id=user_id, server_name=server_name)
            return True

        except Exception as e:
            logger.error("Failed to remove MCP server", 
                        user_id=user_id, server_name=server_name, error=str(e))
            raise MCPError(f"Failed to remove server: {str(e)}")

    async def enable_server(self, user_id: int, server_name: str) -> bool:
        """Enable an MCP server."""
        try:
            # Get server config
            servers = await self.get_user_servers(user_id)
            server = next((s for s in servers if s['server_name'] == server_name), None)
            if not server:
                raise MCPServerNotFoundError(f"Server '{server_name}' not found")

            # Create config object
            config = MCPServerConfig(
                name=server['server_name'],
                server_type=server['server_type'],
                command=server['server_command'],
                args=server['server_args'] or [],
                env=server['server_env'] or {},
                config=server['config'] or {}
            )

            # Add to Claude CLI
            success = await self._add_to_claude_cli(user_id, config)
            if success:
                # Update database
                async with self.storage.db_manager.get_connection() as conn:
                    await conn.execute("""
                        UPDATE user_mcp_servers 
                        SET is_enabled = true, status = 'active', updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND server_name = %s
                    """, (user_id, server_name))
                    await conn.commit()

                logger.info("MCP server enabled successfully", 
                           user_id=user_id, server_name=server_name)
                return True
            else:
                raise MCPError("Failed to add server to Claude CLI")

        except Exception as e:
            logger.error("Failed to enable MCP server", 
                        user_id=user_id, server_name=server_name, error=str(e))
            raise MCPError(f"Failed to enable server: {str(e)}")

    async def disable_server(self, user_id: int, server_name: str) -> bool:
        """Disable an MCP server."""
        try:
            # Remove from Claude CLI
            await self._remove_from_claude_cli(user_id, server_name)

            # Update database
            async with self.storage.db_manager.get_connection() as conn:
                cursor = await conn.execute("""
                    UPDATE user_mcp_servers 
                    SET is_enabled = false, status = 'inactive', updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND server_name = %s
                """, (user_id, server_name))

                if cursor.rowcount == 0:
                    raise MCPServerNotFoundError(f"Server '{server_name}' not found")

                await conn.commit()

            # Clear cache
            cache_key = f"{user_id}:{server_name}"
            self._status_cache.pop(cache_key, None)

            logger.info("MCP server disabled successfully", 
                       user_id=user_id, server_name=server_name)
            return True

        except Exception as e:
            logger.error("Failed to disable MCP server", 
                        user_id=user_id, server_name=server_name, error=str(e))
            raise MCPError(f"Failed to disable server: {str(e)}")

    async def get_server_status(self, user_id: int, server_name: str) -> MCPServerStatus:
        """Get status of an MCP server."""
        cache_key = f"{user_id}:{server_name}"

        # Check cache
        if cache_key in self._status_cache:
            cached_status = self._status_cache[cache_key]
            if cached_status.last_check and \
               (datetime.utcnow() - cached_status.last_check).seconds < self._cache_timeout:
                return cached_status

        # Check actual status
        status = await self._check_server_status(user_id, server_name)

        # Update cache
        self._status_cache[cache_key] = status

        # Update database
        try:
            async with self.storage.db_manager.get_connection() as conn:
                await conn.execute("""
                    UPDATE user_mcp_servers 
                    SET status = %s, last_status_check = CURRENT_TIMESTAMP, 
                        error_message = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND server_name = %s
                """, (status.status, status.error_message, user_id, server_name))
                await conn.commit()
        except Exception as e:
            logger.error("Failed to update server status in database", error=str(e))

        return status

    async def _check_server_status(self, user_id: int, server_name: str) -> MCPServerStatus:
        """Check actual server status via Claude CLI."""
        try:
            start_time = time.time()

            # Use Claude CLI to list servers and check if ours is there
            result = await self._run_claude_command(user_id, ["mcp", "list"])

            response_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # Parse output to check if our server is listed and active
                output = result.stdout.decode('utf-8', errors='ignore')

                # Simple check - look for server name in output
                if server_name in output and "active" in output.lower():
                    return MCPServerStatus(
                        name=server_name,
                        status="active",
                        last_check=datetime.utcnow(),
                        response_time=response_time
                    )
                else:
                    return MCPServerStatus(
                        name=server_name,
                        status="inactive",
                        last_check=datetime.utcnow(),
                        response_time=response_time
                    )
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                return MCPServerStatus(
                    name=server_name,
                    status="error",
                    last_check=datetime.utcnow(),
                    error_message=error_msg,
                    response_time=response_time
                )

        except Exception as e:
            return MCPServerStatus(
                name=server_name,
                status="error",
                last_check=datetime.utcnow(),
                error_message=str(e)
            )

    async def _add_to_claude_cli(self, user_id: int, config: MCPServerConfig) -> bool:
        """Add server to Claude CLI configuration."""
        try:
            # Build Claude MCP add command
            cmd = ["mcp", "add", config.name]

            # Add environment variables
            for key, value in config.env.items():
                cmd.extend(["--env", f"{key}={value}"])

            # Add command separator
            cmd.append("--")

            # Add server command and args
            cmd.append(config.command)
            cmd.extend(config.args)

            result = await self._run_claude_command(user_id, cmd)

            if result.returncode == 0:
                logger.info("Successfully added server to Claude CLI", 
                           server_name=config.name, user_id=user_id)
                return True
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.error("Failed to add server to Claude CLI", 
                           server_name=config.name, user_id=user_id, error=error_msg)
                return False

        except Exception as e:
            logger.error("Exception adding server to Claude CLI", 
                        server_name=config.name, user_id=user_id, error=str(e))
            return False

    async def _remove_from_claude_cli(self, user_id: int, server_name: str) -> bool:
        """Remove server from Claude CLI configuration."""
        try:
            cmd = ["mcp", "remove", server_name]
            result = await self._run_claude_command(user_id, cmd)

            if result.returncode == 0:
                logger.info("Successfully removed server from Claude CLI", 
                           server_name=server_name, user_id=user_id)
                return True
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.warning("Failed to remove server from Claude CLI", 
                             server_name=server_name, user_id=user_id, error=error_msg)
                return False

        except Exception as e:
            logger.error("Exception removing server from Claude CLI", 
                        server_name=server_name, user_id=user_id, error=str(e))
            return False

    async def _run_claude_command(self, user_id: int, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run Claude CLI command with user-specific environment."""
        try:
            # Prepare environment
            env = os.environ.copy()

            # Add user-specific paths or settings if needed
            # For now, we'll use the standard Claude CLI path

            # Build full command
            full_cmd = [self.claude_cli_path] + cmd

            # Run command with timeout
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *full_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                ),
                timeout=30.0
            )

            stdout, stderr = await result.communicate()

            return subprocess.CompletedProcess(
                args=full_cmd,
                returncode=result.returncode,
                stdout=stdout,
                stderr=stderr
            )

        except asyncio.TimeoutError:
            logger.error("Claude CLI command timed out", cmd=cmd, user_id=user_id)
            raise MCPError("Command timed out")
        except Exception as e:
            logger.error("Failed to run Claude CLI command", 
                        cmd=cmd, user_id=user_id, error=str(e))
            raise MCPError(f"Command failed: {str(e)}")

    async def log_usage(self, user_id: int, server_name: str, query: str, 
                       success: bool, response_time: Optional[int] = None,
                       error_message: Optional[str] = None, cost: float = 0.0,
                       session_id: Optional[str] = None) -> None:
        """Log MCP server usage."""
        try:
            async with self.storage.db_manager.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO mcp_usage_log 
                    (user_id, server_name, query, response_time, success, 
                     error_message, cost, session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, server_name, query, response_time, success, 
                     error_message, cost, session_id))
                await conn.commit()

        except Exception as e:
            logger.error("Failed to log MCP usage", error=str(e))

    async def get_usage_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for user."""
        try:
            async with self.storage.db_manager.get_connection() as conn:
                # Total usage stats
                cursor = await conn.execute("""
                    SELECT 
                        COUNT(*) as total_queries,
                        COUNT(DISTINCT server_name) as servers_used,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_queries,
                        AVG(response_time) as avg_response_time,
                        SUM(cost) as total_cost
                    FROM mcp_usage_log
                    WHERE user_id = %s 
                      AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, (user_id, days))

                stats = dict(await cursor.fetchone())

                # Server-specific stats
                cursor = await conn.execute("""
                    SELECT 
                        server_name,
                        COUNT(*) as query_count,
                        AVG(response_time) as avg_response_time,
                        SUM(cost) as total_cost
                    FROM mcp_usage_log
                    WHERE user_id = %s 
                      AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    GROUP BY server_name
                    ORDER BY query_count DESC
                """, (user_id, days))

                server_stats = [dict(row) for row in await cursor.fetchall()]

                return {
                    "overall": stats,
                    "by_server": server_stats,
                    "period_days": days
                }

        except Exception as e:
            logger.error("Failed to get usage stats", user_id=user_id, error=str(e))
            return {"overall": {}, "by_server": [], "period_days": days}
