"""MCP Context Handler.

Handles active context selection and contextual query execution.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.claude.facade import ClaudeIntegration
from src.claude.integration import ClaudeResponse
from src.storage.facade import Storage
from .exceptions import MCPContextError, MCPServerNotFoundError
from .manager import MCPManager

logger = structlog.get_logger()


class MCPContextHandler:
    """Handles MCP context selection and execution."""

    def __init__(self, mcp_manager: MCPManager, claude_integration: ClaudeIntegration, storage: Storage):
        """Initialize context handler."""
        self.mcp_manager = mcp_manager
        self.claude_integration = claude_integration
        self.storage = storage

    async def get_active_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's active MCP context."""
        try:
            async with self.storage.db_manager.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT ac.selected_server, ac.context_settings, ac.selected_at,
                           s.server_type, s.status, t.display_name
                    FROM user_active_context ac
                    LEFT JOIN user_mcp_servers s ON ac.user_id = s.user_id 
                                                 AND ac.selected_server = s.server_name
                    LEFT JOIN mcp_server_templates t ON s.server_type = t.server_type
                    WHERE ac.user_id = %s
                """, (user_id,))

                row = await cursor.fetchone()
                if row:
                    context = dict(row)
                    if context['context_settings']:
                        context['context_settings'] = json.loads(context['context_settings'])
                    return context

                return None

        except Exception as e:
            logger.error("Failed to get active context", user_id=user_id, error=str(e))
            return None

    async def set_active_context(self, user_id: int, server_name: str, 
                               context_settings: Optional[Dict[str, Any]] = None) -> bool:
        """Set user's active MCP context."""
        try:
            # Verify server exists and is enabled
            servers = await self.mcp_manager.get_user_servers(user_id)
            server = next((s for s in servers if s['server_name'] == server_name), None)

            if not server:
                raise MCPServerNotFoundError(f"Server '{server_name}' not found")

            if not server['is_enabled']:
                raise MCPContextError(f"Server '{server_name}' is disabled")

            # Set active context
            async with self.storage.db_manager.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO user_active_context (user_id, selected_server, context_settings)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        selected_server = EXCLUDED.selected_server,
                        context_settings = EXCLUDED.context_settings,
                        selected_at = CURRENT_TIMESTAMP
                """, (user_id, server_name, json.dumps(context_settings or {})))
                await conn.commit()

            logger.info("Active MCP context set", 
                       user_id=user_id, server_name=server_name)
            return True

        except Exception as e:
            logger.error("Failed to set active context", 
                        user_id=user_id, server_name=server_name, error=str(e))
            raise MCPContextError(f"Failed to set context: {str(e)}")

    async def clear_active_context(self, user_id: int) -> bool:
        """Clear user's active MCP context."""
        try:
            async with self.storage.db_manager.get_connection() as conn:
                cursor = await conn.execute("""
                    DELETE FROM user_active_context WHERE user_id = %s
                """, (user_id,))
                await conn.commit()

                logger.info("Active MCP context cleared", 
                           user_id=user_id, affected_rows=cursor.rowcount)
                return cursor.rowcount > 0

        except Exception as e:
            logger.error("Failed to clear active context", user_id=user_id, error=str(e))
            return False

    async def execute_contextual_query(self, user_id: int, query: str,
                                     working_directory: Optional[str] = None,
                                     session_id: Optional[str] = None) -> ClaudeResponse:
        """Execute query with active MCP context."""
        start_time = time.time()

        # Get active context
        context = await self.get_active_context(user_id)
        if not context or not context['selected_server']:
            raise MCPContextError("No active MCP context set. Use /mcpselect first.")

        server_name = context['selected_server']

        try:
            # Check server status
            status = await self.mcp_manager.get_server_status(user_id, server_name)
            if status.status != "active":
                raise MCPContextError(f"Server '{server_name}' is not active (status: {status.status})")

            # Prepare contextual prompt
            contextual_prompt = self._prepare_contextual_prompt(query, context)

            # Execute with Claude CLI using the active MCP server
            response = await self.claude_integration.run_command_with_mcp(
                prompt=contextual_prompt,
                working_directory=working_directory,
                user_id=user_id,
                session_id=session_id,
                mcp_server=server_name
            )

            # Log successful usage
            response_time = int((time.time() - start_time) * 1000)
            await self.mcp_manager.log_usage(
                user_id=user_id,
                server_name=server_name,
                query=query,
                success=True,
                response_time=response_time,
                cost=response.cost,
                session_id=response.session_id
            )

            return response

        except Exception as e:
            # Log failed usage
            response_time = int((time.time() - start_time) * 1000)
            await self.mcp_manager.log_usage(
                user_id=user_id,
                server_name=server_name,
                query=query,
                success=False,
                response_time=response_time,
                error_message=str(e),
                session_id=session_id
            )

            logger.error("MCP contextual query failed", 
                        user_id=user_id, server_name=server_name, 
                        query=query[:100], error=str(e))
            raise

    def _prepare_contextual_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Prepare prompt with MCP context information."""
        server_name = context['selected_server']
        server_type = context.get('server_type', 'unknown')
        display_name = context.get('display_name', server_name)

        # Base contextual prompt
        contextual_prompt = f"""You have access to {display_name} ({server_type}) MCP server tools.

User Query: {query}

Please use the appropriate MCP tools from the {server_name} server to answer this query. 
Be specific and provide detailed results when possible."""

        # Add server-specific context hints
        if server_type == 'github':
            contextual_prompt += "\n\nFor GitHub queries, you can access repositories, issues, pull requests, commits, and other GitHub resources."
        elif server_type == 'filesystem':
            contextual_prompt += "\n\nFor filesystem queries, you can read, write, and manage files in the allowed directories."
        elif server_type in ['postgres', 'sqlite']:
            contextual_prompt += "\n\nFor database queries, you can execute SELECT statements and analyze data. Be careful with data modifications."
        elif server_type == 'git':
            contextual_prompt += "\n\nFor git queries, you can check repository status, history, branches, and perform git operations."
        elif server_type == 'playwright':
            contextual_prompt += "\n\nFor web automation queries, you can browse websites, extract data, and interact with web pages."

        return contextual_prompt

    async def get_context_suggestions(self, user_id: int, query: str) -> List[str]:
        """Get context-aware suggestions based on query and available servers."""
        try:
            # Get user's enabled servers
            servers = await self.mcp_manager.get_user_servers(user_id)
            enabled_servers = [s for s in servers if s['is_enabled']]

            if not enabled_servers:
                return ["Немає активних MCP серверів. Використайте /mcpadd для додавання."]

            suggestions = []
            query_lower = query.lower()

            # Suggest relevant servers based on query content
            for server in enabled_servers:
                server_type = server['server_type']
                server_name = server['server_name']

                if server_type == 'github' and any(word in query_lower for word in 
                    ['github', 'repo', 'repository', 'pull request', 'issue', 'commit']):
                    suggestions.append(f"Використати {server_name} (GitHub) для цього запиту")

                elif server_type == 'filesystem' and any(word in query_lower for word in
                    ['file', 'directory', 'read', 'write', 'save', 'файл', 'папка']):
                    suggestions.append(f"Використати {server_name} (File System) для роботи з файлами")

                elif server_type in ['postgres', 'sqlite'] and any(word in query_lower for word in
                    ['database', 'query', 'select', 'sql', 'table', 'бд', 'база даних']):
                    suggestions.append(f"Використати {server_name} (Database) для запитів до БД")

                elif server_type == 'git' and any(word in query_lower for word in
                    ['git', 'branch', 'merge', 'commit', 'status']):
                    suggestions.append(f"Використати {server_name} (Git) для git операцій")

                elif server_type == 'playwright' and any(word in query_lower for word in
                    ['web', 'browser', 'scrape', 'webpage', 'site', 'сайт']):
                    suggestions.append(f"Використати {server_name} (Web Automation) для веб-задач")

            # If no specific suggestions, show general options
            if not suggestions:
                for server in enabled_servers[:3]:  # Show top 3 servers
                    suggestions.append(f"Спробувати з {server['server_name']} ({server.get('display_name', server['server_type'])})")

            return suggestions

        except Exception as e:
            logger.error("Failed to get context suggestions", user_id=user_id, error=str(e))
            return ["Помилка при отриманні пропозицій контексту"]

    async def get_context_summary(self, user_id: int) -> Dict[str, Any]:
        """Get summary of user's MCP context and usage."""
        try:
            # Get active context
            active_context = await self.get_active_context(user_id)

            # Get all user servers
            servers = await self.mcp_manager.get_user_servers(user_id)

            # Get usage stats
            usage_stats = await self.mcp_manager.get_usage_stats(user_id, days=7)

            return {
                "active_context": active_context,
                "total_servers": len(servers),
                "enabled_servers": len([s for s in servers if s['is_enabled']]),
                "server_types": list(set(s['server_type'] for s in servers)),
                "recent_usage": usage_stats
            }

        except Exception as e:
            logger.error("Failed to get context summary", user_id=user_id, error=str(e))
            return {}
