# Prompt for Perplexity Lab: Claude Architect Bot (Telegram UserBot)

## Project Overview
Create a comprehensive implementation of a Telegram UserBot using the moonuserbot framework that serves as a **Claude Architect Bot**. This bot will work in collaboration with an existing Claude Developer Bot, forming a software development team where:
- **Claude Developer Bot**: Handles coding, implementation, debugging
- **Claude Architect Bot**: Manages architecture, design decisions, code reviews, project planning
- **Human CEO**: Provides high-level direction and project requirements

## Core Requirements

### 1. Technical Foundation
```python
# Base moonuserbot integration requirements:
- Python 3.11+ with asyncio support
- Telethon library for Telegram UserBot functionality
- MCP (Model Context Protocol) integration for project access
- Secure session management and authentication
- Multi-chat support with role-based permissions
```

### 2. Architectural Responsibilities
The Architect Bot should handle:

#### Project Planning & Design
- Analyze project requirements and create technical specifications
- Design system architecture and component interactions
- Create and maintain project roadmaps and milestones
- Suggest technology stack and framework decisions
- Plan database schemas and API designs

#### Code Quality & Standards
- Perform automated code reviews on commits/PRs
- Enforce coding standards and best practices
- Suggest refactoring opportunities
- Monitor technical debt and complexity metrics
- Ensure SOLID principles and design patterns compliance

#### Documentation & Communication
- Generate and maintain technical documentation
- Create architecture diagrams and system flows
- Facilitate communication between team members
- Translate business requirements into technical tasks
- Maintain project knowledge base

### 3. Security Framework

#### Authentication & Authorization
```python
SECURITY_CONFIG = {
    "allowed_users": ["developer_bot_id", "ceo_user_id"],
    "allowed_groups": ["project_development_group_id"],
    "admin_users": ["ceo_user_id"],
    "sensitive_commands": ["deploy", "delete", "production"],
    "rate_limiting": {
        "max_commands_per_minute": 30,
        "max_file_operations_per_hour": 100
    }
}
```

#### Data Protection
- Encrypt sensitive project data
- Implement secure file handling
- Audit all bot actions and decisions
- Protect API keys and credentials
- Secure MCP connections

#### Access Control
- Project directory access restrictions
- Command-level permissions
- Time-based access controls
- Emergency shutdown mechanisms

### 4. Development Methodology Integration

#### Agile/Scrum Support
- Sprint planning assistance
- User story analysis and breakdown
- Estimation support (story points)
- Sprint retrospective insights
- Backlog prioritization suggestions

#### CI/CD Integration
- Code quality gates
- Automated testing coordination
- Deployment pipeline oversight
- Environment management
- Release planning and coordination

#### Testing Strategy
- Test plan generation
- Coverage analysis
- Test case suggestions
- Integration test coordination
- Performance testing guidelines

### 5. Advanced Features

#### AI-Powered Analysis
```python
class ArchitectureAnalyzer:
    async def analyze_project_structure(self):
        """Analyze project architecture and suggest improvements"""

    async def detect_anti_patterns(self):
        """Identify architectural anti-patterns"""

    async def suggest_optimizations(self):
        """Recommend performance and maintainability improvements"""

    async def assess_scalability(self):
        """Evaluate system scalability potential"""
```

#### MCP Integration
- Real-time project file monitoring
- Automatic documentation updates
- Code dependency analysis
- Configuration management
- Database schema evolution tracking

#### Communication Protocols
```python
COMMUNICATION_PATTERNS = {
    "daily_standups": {
        "trigger": "scheduled_daily",
        "participants": ["developer_bot", "ceo"],
        "format": "progress_summary"
    },
    "code_reviews": {
        "trigger": "commit_detected",
        "action": "automated_review",
        "escalation": "complex_changes"
    },
    "architecture_decisions": {
        "trigger": "major_changes",
        "process": "rfc_style_discussion",
        "approval": "ceo_required"
    }
}
```

### 6. Bot Personality & Behavior

#### Communication Style
- Professional but approachable
- Clear technical explanations
- Constructive feedback approach
- Proactive problem identification
- Collaborative decision-making

#### Decision-Making Framework
- Data-driven architecture choices
- Risk assessment for major decisions
- Performance vs. complexity trade-offs
- Future scalability considerations
- Maintainability prioritization

### 7. Implementation Structure

#### Core Modules
```python
project_structure = {
    "core/": {
        "bot.py": "Main UserBot implementation",
        "architect.py": "Architecture analysis engine",
        "communicator.py": "Team communication handler",
        "security.py": "Security and permissions manager"
    },
    "analyzers/": {
        "code_quality.py": "Code review and quality checks",
        "architecture.py": "System design analysis",
        "performance.py": "Performance assessment",
        "security_scan.py": "Security vulnerability detection"
    },
    "integrations/": {
        "mcp_client.py": "MCP protocol implementation",
        "git_hooks.py": "Git integration for code monitoring",
        "ci_cd.py": "CI/CD pipeline integration",
        "documentation.py": "Auto-documentation generator"
    },
    "utils/": {
        "templates.py": "Architecture templates and patterns",
        "metrics.py": "Code and architecture metrics",
        "notifications.py": "Team notification system"
    }
}
```

#### Configuration Management
```python
ARCHITECT_CONFIG = {
    "project_access": {
        "base_directory": "/path/to/project",
        "allowed_extensions": [".py", ".js", ".ts", ".md", ".yml"],
        "protected_files": ["secrets.env", "production.config"]
    },
    "analysis_settings": {
        "complexity_threshold": 10,
        "coverage_minimum": 80,
        "performance_benchmarks": {...}
    },
    "communication": {
        "update_frequency": "real_time",
        "summary_schedule": "daily_9am",
        "escalation_rules": {...}
    }
}
```

### 8. Potential Security Challenges & Solutions

#### Challenge: UserBot Permissions
- **Risk**: Excessive Telegram permissions
- **Solution**: Minimal permission principle, regular audits

#### Challenge: Project File Access
- **Risk**: Unauthorized file modifications
- **Solution**: Read-only by default, explicit write permissions

#### Challenge: Communication Interception
- **Risk**: Sensitive project data exposure
- **Solution**: End-to-end encryption, secure channels

#### Challenge: Bot Impersonation
- **Risk**: Malicious actors mimicking the bot
- **Solution**: Cryptographic signatures, verification protocols

### 9. Testing Framework

#### Unit Testing
- Architecture analysis algorithm tests
- Communication protocol tests
- Security permission tests
- MCP integration tests

#### Integration Testing
- End-to-end workflow tests
- Multi-bot collaboration tests
- Real project scenario tests
- Performance under load tests

#### Security Testing
- Permission bypass attempts
- Data leakage tests
- Authentication failure handling
- Rate limiting effectiveness

### 10. Monitoring & Analytics

#### Performance Metrics
- Response time to developer requests
- Code review accuracy and speed
- Architecture decision quality
- Team productivity improvements

#### Health Monitoring
- Bot uptime and availability
- Error rates and types
- Resource utilization
- Communication effectiveness

## Expected Deliverables

1. **Complete moonuserbot implementation** with all core features
2. **Comprehensive security framework** with access controls
3. **MCP integration** for project file access
4. **Testing suite** with >90% coverage
5. **Documentation** including setup, configuration, and usage guides
6. **Deployment scripts** for production environment
7. **Monitoring dashboard** for bot performance tracking

## Success Criteria

- Bot successfully collaborates with Developer Bot
- Demonstrates measurable improvement in code quality
- Provides valuable architectural insights and decisions
- Maintains security standards without compromising functionality
- Integrates seamlessly with existing development workflow
- Shows potential for scaling to larger development teams

Please provide a complete, production-ready implementation that addresses all these requirements with modern software engineering practices.