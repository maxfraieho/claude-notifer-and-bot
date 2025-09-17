"""Claude CLI Integration with MCP Support.

Extends the existing Claude integration to support MCP server context execution.
"""

import asyncio
import json
import os
import subprocess
from typing import Any, Dict, Optional

import structlog

from ..claude.integration import ClaudeIntegration, ClaudeResponse
from ..exceptions import ClaudeProcessError

logger = structlog.get_logger()


class ClaudeMCPIntegration(ClaudeIntegration):
    """Extended Claude integration with MCP support."""

    async def run_command_with_mcp(self, prompt: str, working_directory: str,
                                 user_id: int, mcp_server: str,
                                 session_id: Optional[str] = None) -> ClaudeResponse:
        """Run Claude command with specific MCP server context."""

        logger.info("Running Claude command with MCP context", 
                   user_id=user_id, mcp_server=mcp_server, 
                   working_directory=working_directory)

        # Build Claude CLI command with MCP context
        cmd = [self.claude_cli_path or "claude"]

        # Add session handling
        if session_id:
            cmd.extend(["--session", session_id])

        # Add working directory
        if working_directory and working_directory != str(self.config.approved_directory):
            cmd.extend(["--directory", working_directory])

        # Add MCP server specification (if Claude CLI supports it)
        # Note: This depends on Claude CLI MCP implementation
        # cmd.extend(["--mcp-server", mcp_server])

        # Add prompt
        if prompt.strip():
            cmd.append(prompt)
        else:
            cmd.append("--continue")  # Continue previous conversation

        try:
            result = await self._execute_claude_command(cmd, working_directory, user_id)

            # Parse the response
            response = self._parse_claude_output(result.stdout, result.stderr, result.returncode)

            # Log MCP usage
            if hasattr(self, 'mcp_manager') and self.mcp_manager:
                success = not response.is_error
                await self.mcp_manager.log_usage(
                    user_id=user_id,
                    server_name=mcp_server,
                    query=prompt,
                    success=success,
                    response_time=response.duration_ms,
                    error_message=response.error_type if response.is_error else None,
                    cost=response.cost,
                    session_id=response.session_id
                )

            return response

        except Exception as e:
            logger.error("MCP command execution failed", 
                        user_id=user_id, mcp_server=mcp_server, error=str(e))
            raise ClaudeProcessError(f"MCP command failed: {str(e)}")

    async def list_mcp_servers(self, user_id: int) -> Dict[str, Any]:
        """List available MCP servers via Claude CLI."""
        try:
            cmd = [self.claude_cli_path or "claude", "mcp", "list"]
            result = await self._execute_claude_command(cmd, None, user_id)

            if result.returncode == 0:
                # Parse MCP server list from output
                output = result.stdout.decode('utf-8', errors='ignore')
                return self._parse_mcp_list_output(output)
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.error("Failed to list MCP servers", 
                           user_id=user_id, error=error_msg)
                return {"servers": [], "error": error_msg}

        except Exception as e:
            logger.error("Error listing MCP servers", user_id=user_id, error=str(e))
            return {"servers": [], "error": str(e)}

    async def add_mcp_server(self, user_id: int, server_name: str, 
                           command: str, args: list, env: Dict[str, str]) -> bool:
        """Add MCP server via Claude CLI."""
        try:
            # Build Claude MCP add command
            cmd = [self.claude_cli_path or "claude", "mcp", "add", server_name]

            # Add environment variables
            for key, value in env.items():
                cmd.extend(["--env", f"{key}={value}"])

            # Add command separator
            cmd.append("--")

            # Add server command and args
            cmd.append(command)
            cmd.extend(args)

            result = await self._execute_claude_command(cmd, None, user_id)

            if result.returncode == 0:
                logger.info("Successfully added MCP server", 
                           server_name=server_name, user_id=user_id)
                return True
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.error("Failed to add MCP server", 
                           server_name=server_name, user_id=user_id, error=error_msg)
                return False

        except Exception as e:
            logger.error("Error adding MCP server", 
                        server_name=server_name, user_id=user_id, error=str(e))
            return False

    async def remove_mcp_server(self, user_id: int, server_name: str) -> bool:
        """Remove MCP server via Claude CLI."""
        try:
            cmd = [self.claude_cli_path or "claude", "mcp", "remove", server_name]
            result = await self._execute_claude_command(cmd, None, user_id)

            if result.returncode == 0:
                logger.info("Successfully removed MCP server", 
                           server_name=server_name, user_id=user_id)
                return True
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.warning("Failed to remove MCP server", 
                             server_name=server_name, user_id=user_id, error=error_msg)
                return False

        except Exception as e:
            logger.error("Error removing MCP server", 
                        server_name=server_name, user_id=user_id, error=str(e))
            return False

    def _parse_mcp_list_output(self, output: str) -> Dict[str, Any]:
        """Parse MCP server list output from Claude CLI."""
        servers = []
        lines = output.strip().split('\n')

        current_server = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for server entries (this is a simplified parser)
            if line.startswith('✓') or line.startswith('✗') or line.startswith('○'):
                # Server status line
                parts = line.split()
                if len(parts) >= 2:
                    status_char = parts[0]
                    server_name = parts[1]

                    status = "active" if status_char == "✓" else ("error" if status_char == "✗" else "inactive")

                    current_server = {
                        "name": server_name,
                        "status": status,
                        "details": " ".join(parts[2:]) if len(parts) > 2 else ""
                    }
                    servers.append(current_server)
            elif current_server and line.startswith(' '):
                # Additional server details
                if 'details' not in current_server:
                    current_server['details'] = ''
                current_server['details'] += ' ' + line.strip()

        return {
            "servers": servers,
            "raw_output": output
        }

    async def check_mcp_server_status(self, user_id: int, server_name: str) -> Dict[str, Any]:
        """Check status of specific MCP server."""
        try:
            # Use the list command and filter for our server
            mcp_list = await self.list_mcp_servers(user_id)

            if "error" in mcp_list:
                return {"status": "error", "error": mcp_list["error"]}

            # Find our server in the list
            for server in mcp_list.get("servers", []):
                if server["name"] == server_name:
                    return {
                        "status": server["status"],
                        "details": server.get("details", ""),
                        "found": True
                    }

            return {"status": "not_found", "found": False}

        except Exception as e:
            logger.error("Error checking MCP server status", 
                        server_name=server_name, user_id=user_id, error=str(e))
            return {"status": "error", "error": str(e)}


# Factory function to create the enhanced Claude integration
def create_claude_mcp_integration(config, process_manager=None, sdk_manager=None, 
                                session_manager=None, tool_monitor=None, mcp_manager=None):
    """Create Claude integration with MCP support."""
    integration = ClaudeMCPIntegration(
        config=config,
        process_manager=process_manager,
        sdk_manager=sdk_manager,
        session_manager=session_manager,
        tool_monitor=tool_monitor
    )

    # Attach MCP manager for usage logging
    integration.mcp_manager = mcp_manager

    return integration
