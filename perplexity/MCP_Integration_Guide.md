# MCP Integration Guide for Claude Code Telegram Bot

## Overview
This guide explains how to integrate the MCP (Model Context Protocol) management system into the existing Claude Code Telegram Bot.

## Architecture
The MCP system adds the following components:
- Database tables for server management
- MCP Manager for server operations
- Context Handler for query execution
- Server Configuration Templates
- Telegram command handlers
- Ukrainian localization

## Integration Steps

### 1. Database Setup
Run the migration to add MCP tables:
```sql
-- Execute mcp_migration.sql
```

### 2. Directory Structure
Add the following files to your project:

```
src/
├── mcp/
│   ├── __init__.py          # Module initialization
│   ├── manager.py           # Core MCP management
│   ├── context_handler.py   # Context handling
│   ├── server_configs.py    # Server templates
│   ├── exceptions.py        # MCP-specific exceptions
│   └── claude_integration.py # Extended Claude integration
├── bot/handlers/
│   ├── mcp_commands.py      # MCP command handlers
│   └── mcp_callbacks.py     # Callback handlers
└── localization/translations/
    └── uk.json              # Updated with MCP translations
```

### 3. Main Application Updates

#### Update main.py dependencies creation:
```python
async def create_application(config: Settings) -> Dict[str, Any]:
    # ... existing code ...

    # Create MCP components
    from src.mcp import MCPManager, MCPContextHandler
    from src.mcp.claude_integration import create_claude_mcp_integration

    # Create MCP manager
    mcp_manager = MCPManager(config, storage)

    # Create enhanced Claude integration with MCP support
    claude_integration = create_claude_mcp_integration(
        config=config,
        process_manager=process_manager,
        sdk_manager=sdk_manager,
        session_manager=session_manager,
        tool_monitor=tool_monitor,
        mcp_manager=mcp_manager
    )

    # Create MCP context handler
    mcp_context_handler = MCPContextHandler(
        mcp_manager=mcp_manager,
        claude_integration=claude_integration,
        storage=storage
    )

    # Add to dependencies
    dependencies.update({
        "mcp_manager": mcp_manager,
        "mcp_context_handler": mcp_context_handler,
    })

    # Update claude_integration in dependencies
    dependencies["claude_integration"] = claude_integration
```

#### Update bot command registration:
```python
# In ClaudeCodeBot._register_handlers()
from .handlers import mcp_commands

# Add MCP command handlers
mcp_handlers = [
    ("mcpadd", mcp_commands.mcpadd_command),
    ("mcplist", mcp_commands.mcplist_command),
    ("mcpselect", mcp_commands.mcpselect_command),
    ("mcpask", mcp_commands.mcpask_command),
    ("mcpremove", mcp_commands.mcpremove_command),
    ("mcpstatus", mcp_commands.mcpstatus_command),
]

for cmd, handler in mcp_handlers:
    self.app.add_handler(CommandHandler(cmd, self._inject_deps(handler)))
```

#### Update callback handling:
```python
# In callback.py handle_callback_query()
from ..handlers.mcp_callbacks import handle_mcp_callback

# Add MCP callback routing
if data.startswith("mcp_"):
    await handle_mcp_callback(update, context)
    return
```

### 4. Localization Updates
Merge the MCP translations into your existing uk.json file:
```json
{
  "existing_translations": "...",
  "mcp": {
    // Content from mcp_localization_uk.json
  }
}
```

### 5. Configuration Updates
Add MCP settings to your Settings class:
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # MCP settings
    enable_mcp: bool = Field(True, description="Enable MCP server management")
    mcp_max_servers_per_user: int = Field(10, description="Max MCP servers per user")
    mcp_claude_cli_path: Optional[str] = Field(None, description="Path to Claude CLI for MCP")
```

### 6. Docker Updates (if using Docker)
Add Node.js for MCP servers that require npx:
```dockerfile
# Add to Dockerfile
RUN apt-get update && apt-get install -y nodejs npm
```

## Usage Examples

### Adding a GitHub server:
```
User: /mcpadd
Bot: [Shows server type selection menu]
User: [Selects GitHub]
Bot: [Wizard asks for GitHub token]
User: [Provides token]
Bot: [Wizard asks for server name]
User: github-main
Bot: ✅ Server 'github-main' successfully added!
```

### Using MCP context:
```
User: /mcpselect github-main
Bot: ✅ Active context set: github-main

User: /mcpask Show recent pull requests
Bot: [Executes query with GitHub MCP context]
```

### Listing servers:
```
User: /mcplist
Bot: 📋 MCP Servers:

✅ github-main - GitHub Integration
   Status: connected
   Last used: 10 min ago

🔧 filesystem-project - File System Access  
   Status: connected
   Directory: /home/user/project
```

## Security Considerations

1. **Token Storage**: GitHub tokens and database credentials are stored securely in the database
2. **Path Validation**: Filesystem paths are validated to prevent directory traversal
3. **Server Limits**: Users are limited to 10 MCP servers maximum
4. **Command Validation**: All MCP commands are validated before execution
5. **Error Handling**: Comprehensive error handling prevents system crashes

## Troubleshooting

### Common Issues:
1. **Claude CLI not found**: Set `claude_cli_path` in configuration
2. **MCP server fails to start**: Check server dependencies (Node.js, Python packages)
3. **Permission errors**: Ensure proper file system permissions for filesystem servers
4. **Database connection fails**: Verify PostgreSQL connection strings

### Logging:
All MCP operations are logged with structured logging:
```python
logger.info("MCP server added", user_id=user_id, server_name=server_name, server_type=server_type)
```

## Future Enhancements

1. **Server Health Monitoring**: Periodic health checks for MCP servers
2. **Usage Analytics**: Detailed usage statistics and reporting
3. **Server Templates**: More predefined server configurations
4. **Backup/Restore**: Export/import server configurations
5. **Team Sharing**: Share MCP servers between team members

## API Reference

### MCPManager
- `add_server(user_id, config)`: Add new MCP server
- `remove_server(user_id, server_name)`: Remove MCP server
- `get_user_servers(user_id)`: Get user's servers
- `get_server_status(user_id, server_name)`: Check server status

### MCPContextHandler  
- `set_active_context(user_id, server_name)`: Set active context
- `execute_contextual_query(user_id, query)`: Execute query with context
- `get_context_suggestions(user_id, query)`: Get context suggestions

This integration provides a complete MCP management system that seamlessly integrates with the existing Claude Code Telegram Bot architecture.
