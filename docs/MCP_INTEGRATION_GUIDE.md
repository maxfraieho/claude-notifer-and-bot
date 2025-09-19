# 🔌 MCP (Model Context Protocol) Integration Guide

## Overview

The Model Context Protocol (MCP) integration allows the Claude Code Telegram Bot to connect with external tools and services, significantly expanding Claude's capabilities beyond its core functionality.

## What is MCP?

MCP is a protocol that enables AI assistants to securely connect with external data sources and tools. It provides:

- **Enhanced Context** - Access to real-time data and specialized tools
- **Secure Integration** - Sandboxed execution with proper access controls
- **Extensible Architecture** - Easy addition of new capabilities
- **Standardized Interface** - Consistent way to interact with diverse tools

## 🚀 Getting Started

### Enable MCP Support

1. **Configuration**: Set in your environment
   ```bash
   ENABLE_MCP=true
   MCP_CONFIG_PATH=/path/to/mcp-config.json
   ```

2. **Check Status**: Verify MCP is enabled
   ```
   /mcpstatus
   ```

### Your First MCP Server

```
/mcpadd filesystem
```
This adds a filesystem server that enhances file operations.

## 📋 MCP Commands Reference

### Server Management

#### `/mcpadd` - Add MCP Server
Add and configure new MCP servers.

**Interactive Mode:**
```
/mcpadd
```
- Shows available server types
- Guided configuration wizard
- Automatic validation and testing

**Direct Mode:**
```
/mcpadd <server_type>
```
Supported server types:
- `filesystem` - Enhanced file operations
- `database` - SQL database integration
- `web` - Web scraping and API access
- `git` - Advanced git operations
- `docker` - Container management
- `custom` - User-defined servers

#### `/mcplist` - List Servers
Display all configured MCP servers.

```
/mcplist
```

**Output includes:**
- Server name and type
- Connection status (🟢 active, 🔴 inactive, 🟡 error)
- Available tools count
- Last used timestamp
- Usage statistics

#### `/mcpselect` - Select Active Context
Choose which MCP server context to use for enhanced queries.

**Interactive Selection:**
```
/mcpselect
```
Shows server browser with:
- Server capabilities
- Tool descriptions
- Usage recommendations

**Direct Selection:**
```
/mcpselect filesystem
/mcpselect database
```

#### `/mcpask` - Enhanced Queries
Ask questions with MCP context for enhanced capabilities.

```
/mcpask How many Python files are in this project?
/mcpask Show me the database schema
/mcpask What's the latest commit in the repository?
```

**Benefits:**
- Access to real-time data
- Specialized tool capabilities
- Enhanced accuracy and context
- Automated multi-step operations

#### `/mcpremove` - Remove Server
Safely remove MCP server configurations.

**Interactive Removal:**
```
/mcpremove
```
- Shows server list with usage stats
- Confirms removal with warnings
- Handles cleanup automatically

**Direct Removal:**
```
/mcpremove filesystem
```

#### `/mcpstatus` - System Status
Comprehensive MCP system health and statistics.

```
/mcpstatus
```

**Information displayed:**
- System-wide MCP status
- Server connection health
- Total tools available
- Usage statistics
- Error logs and diagnostics
- Performance metrics

## 🛠️ Built-in MCP Servers

### Filesystem Server
Enhanced file and directory operations.

**Capabilities:**
- Recursive directory analysis
- Advanced file searching
- Batch operations
- File metadata extraction
- Content analysis

**Example usage:**
```
/mcpselect filesystem
/mcpask Find all TODO comments in Python files
/mcpask Show me files modified in the last week
/mcpask What's the total lines of code in this project?
```

### Database Server
SQL database integration and querying.

**Supported databases:**
- SQLite
- PostgreSQL
- MySQL
- MongoDB (via adapter)

**Capabilities:**
- Schema introspection
- Query execution
- Data analysis
- Migration assistance
- Performance monitoring

**Example usage:**
```
/mcpselect database
/mcpask Show me the user table schema
/mcpask How many active users do we have?
/mcpask Find users created last month
```

### Web Server
Web scraping and API integration.

**Capabilities:**
- HTTP requests
- HTML parsing
- API integration
- Data extraction
- Content monitoring

**Example usage:**
```
/mcpselect web
/mcpask Check if our website is responding
/mcpask Get the latest news from our RSS feed
/mcpask What's the current status of GitHub API?
```

### Git Server
Advanced git repository operations.

**Capabilities:**
- Repository analysis
- Commit history mining
- Branch operations
- Code statistics
- Collaboration insights

**Example usage:**
```
/mcpselect git
/mcpask Who contributed most to this project?
/mcpask Show me commits from last sprint
/mcpask What files change most frequently?
```

## 🔧 Custom MCP Servers

### Creating Custom Servers

1. **Server Definition**: Create server configuration
   ```json
   {
     "name": "custom-api",
     "type": "custom",
     "config": {
       "command": "python",
       "args": ["custom_server.py"],
       "env": {
         "API_KEY": "your-api-key"
       }
     },
     "tools": {
       "api_query": {
         "description": "Query custom API",
         "parameters": {
           "endpoint": "string",
           "params": "object"
         }
       }
     }
   }
   ```

2. **Server Implementation**: Python example
   ```python
   import json
   import sys
   from typing import Any, Dict

   class CustomMCPServer:
       def __init__(self):
           self.tools = {
               "api_query": self.api_query
           }

       async def api_query(self, endpoint: str, params: Dict[str, Any]):
           # Your custom API logic here
           return {"result": "API response data"}

       async def handle_request(self, request: Dict[str, Any]):
           tool_name = request.get("tool")
           if tool_name in self.tools:
               return await self.tools[tool_name](**request.get("params", {}))
           return {"error": f"Unknown tool: {tool_name}"}

   if __name__ == "__main__":
       server = CustomMCPServer()
       # Handle MCP protocol communication
   ```

3. **Registration**: Add via bot
   ```
   /mcpadd custom
   [Follow configuration wizard]
   ```

### Server Templates

Common server patterns and templates:

**API Integration Server:**
```python
# Template for REST API integration
class APIServer(MCPServer):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def api_call(self, endpoint: str, method: str = "GET", data: dict = None):
        # HTTP request logic
        pass
```

**Database Server:**
```python
# Template for database integration
class DatabaseServer(MCPServer):
    def __init__(self, connection_string: str):
        self.db = connect(connection_string)

    async def query(self, sql: str, params: list = None):
        # Database query logic
        pass
```

## 🔒 Security & Permissions

### Security Model
MCP servers run in sandboxed environments with:

- **Process isolation** - Each server runs in separate process
- **Resource limits** - CPU, memory, and network restrictions
- **Permission system** - Granular access controls
- **Audit logging** - All operations logged for security

### Permission Management

**Server Permissions:**
```json
{
  "permissions": {
    "filesystem": {
      "read": ["/approved/directory/*"],
      "write": ["/approved/directory/temp/*"],
      "execute": false
    },
    "network": {
      "allowed_hosts": ["api.example.com"],
      "allowed_ports": [80, 443]
    },
    "system": {
      "environment_vars": ["API_KEY"],
      "subprocess": false
    }
  }
}
```

**Access Control:**
- User-level permissions
- Server-level restrictions
- Tool-specific limitations
- Resource quotas

### Best Practices

1. **Principle of least privilege** - Grant minimum required permissions
2. **Input validation** - Sanitize all user inputs
3. **Output filtering** - Filter sensitive information from responses
4. **Regular audits** - Monitor server usage and access patterns
5. **Update management** - Keep servers and dependencies updated

## 📊 Monitoring & Analytics

### Usage Analytics

Track MCP usage with built-in analytics:

```
/mcpstatus
```

**Metrics available:**
- Tool usage frequency
- Response times
- Error rates
- Resource utilization
- User activity patterns

### Performance Monitoring

**Server Health Checks:**
- Connection status monitoring
- Response time tracking
- Error rate analysis
- Resource usage monitoring

**Alerting:**
- Server downtime notifications
- Performance degradation alerts
- Error threshold warnings
- Resource limit notifications

### Logging and Debugging

**Debug Mode:**
```bash
# Enable MCP debug logging
python -m src.main --debug
```

**Log Categories:**
- Server communication
- Tool executions
- Permission checks
- Error diagnostics
- Performance metrics

## 🔄 Integration Workflows

### Development Workflow

1. **Project Analysis:**
   ```
   /mcpselect filesystem
   /mcpask Analyze project structure and dependencies
   ```

2. **Database Operations:**
   ```
   /mcpselect database
   /mcpask Show me recent user activity
   ```

3. **API Integration:**
   ```
   /mcpselect web
   /mcpask Check external service status
   ```

4. **Git Operations:**
   ```
   /mcpselect git
   /mcpask Show me commits since last release
   ```

### Automated Workflows

**CI/CD Integration:**
- Pre-deployment checks
- Database migrations
- API health monitoring
- Performance testing

**Monitoring:**
- System health checks
- Error tracking
- Performance monitoring
- Alerting integration

## 🚨 Troubleshooting

### Common Issues

#### "MCP server not responding"
**Symptoms:** Server shows as inactive in `/mcplist`
**Solutions:**
1. Check server process status
2. Verify configuration settings
3. Review server logs for errors
4. Restart server if needed

#### "Permission denied" errors
**Symptoms:** Tools fail with permission errors
**Solutions:**
1. Review server permissions configuration
2. Check file/directory access rights
3. Verify user authentication
4. Update permission settings

#### "Tool not found" errors
**Symptoms:** `/mcpask` fails with unknown tool
**Solutions:**
1. Verify server is selected with `/mcpselect`
2. Check available tools with `/mcplist`
3. Confirm server configuration
4. Re-register server if needed

### Debug Strategies

1. **Check system status**: `/mcpstatus`
2. **Review server logs**: Enable debug mode
3. **Test individual tools**: Use specific tool commands
4. **Verify permissions**: Check access controls
5. **Restart services**: Remove and re-add servers

### Performance Optimization

**Server Optimization:**
- Connection pooling
- Response caching
- Batch operations
- Resource limits tuning

**Query Optimization:**
- Specific tool selection
- Optimized parameters
- Result filtering
- Timeout configuration

## 📚 Examples and Use Cases

### Code Analysis
```
/mcpselect filesystem
/mcpask Find all functions longer than 50 lines
/mcpask Show me duplicate code patterns
/mcpask What are the most complex functions?
```

### Database Management
```
/mcpselect database
/mcpask Show me table sizes and row counts
/mcpask Find queries that take longer than 1 second
/mcpask Generate a backup of user preferences
```

### API Monitoring
```
/mcpselect web
/mcpask Check all external API endpoints
/mcpask Monitor response times for critical services
/mcpask Validate API key permissions
```

### Project Insights
```
/mcpselect git
/mcpask Show me contribution statistics by developer
/mcpask Find files that haven't been modified in 6 months
/mcpask Generate a changelog since last release
```

## 🔮 Future Enhancements

### Planned Features
- **Visual server builder** - GUI for server configuration
- **Server marketplace** - Community-contributed servers
- **Advanced caching** - Intelligent response caching
- **Real-time streaming** - Live data feeds
- **Multi-server queries** - Cross-server operations

### Roadmap
- **Q4 2024**: Visual server builder
- **Q1 2025**: Server marketplace launch
- **Q2 2025**: Advanced caching system
- **Q3 2025**: Real-time streaming support

---

## Quick Reference

**Enable MCP**: `ENABLE_MCP=true` in configuration
**Add server**: `/mcpadd <type>`
**List servers**: `/mcplist`
**Select context**: `/mcpselect <server>`
**Enhanced query**: `/mcpask <question>`
**Remove server**: `/mcpremove <server>`
**System status**: `/mcpstatus`

**Built-in servers**: filesystem, database, web, git
**Security**: Sandboxed execution, permission system
**Monitoring**: Usage analytics, health checks, logging

For detailed technical documentation, see the MCP specification and server development guides.