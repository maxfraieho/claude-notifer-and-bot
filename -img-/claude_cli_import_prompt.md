# Claude CLI Prompt: Intelligent Integration of /img Command Implementation

## Context & Project Overview

I have a Claude Code Telegram Bot project with the following established architecture:

**Current Project Structure:**
```
├── bot/                    # Telegram bot logic
│   ├── features/           # Bot features and extensions
│   ├── handlers/           # Event handlers
│   ├── middleware/         # Security, auth, rate limiting
│   ├── utils/             # Bot utilities
│   └── core.py            # Main bot class
├── claude/                 # Claude CLI/SDK integration
├── config/                 # Configuration management
├── localization/           # Multi-language support
├── security/               # Security components
├── storage/                # Database layer
├── utils/                  # General utilities
└── main.py                # Entry point
```

**Tech Stack:** Python 3.11+, asyncio, Telegram Bot API, Pydantic, SQLite, structlog

## Objective

I need you to intelligently analyze my existing codebase and implement a comprehensive `/img` command functionality based on the detailed implementation provided in `image_command_implementation.md`. 

## Implementation Requirements

### 1. Intelligent Code Analysis
Before making any changes, please:

1. **Analyze existing patterns** in my codebase:
   - How are other commands structured and registered?
   - What are the existing naming conventions?
   - How is dependency injection handled?
   - What error handling patterns are used?
   - How are database operations structured?

2. **Identify integration points** where new code needs to connect:
   - Handler registration in `bot/core.py`
   - Database schema updates and migrations
   - Configuration additions in `config/settings.py`
   - Localization file updates
   - Security validator extensions

3. **Assess compatibility** between the provided implementation and existing code:
   - Check for naming conflicts
   - Verify import paths match project structure
   - Ensure async patterns are consistent
   - Validate database connection patterns

### 2. Smart Implementation Strategy

**Phase 1: Foundation Setup**
- Add required dependencies (Pillow, aiofiles) to requirements
- Create image-related configuration settings
- Implement database schema migrations
- Set up temporary directory structure

**Phase 2: Core Components**
- Implement `ImageProcessor` class with existing security patterns
- Create `ClaudeImageIntegration` following existing Claude integration patterns
- Build `ImageCommandHandler` using established handler patterns

**Phase 3: Integration**
- Register new handlers in bot core
- Update message handlers for image session management
- Integrate with existing middleware and security
- Add localization entries

**Phase 4: Testing & Validation**
- Create test scenarios for image processing workflow
- Validate error handling and security measures
- Test Claude CLI integration
- Verify session management and cleanup

### 3. Code Adaptation Guidelines

**Maintain Consistency:**
- Follow existing code style, naming conventions, and patterns
- Use the same logging, error handling, and validation approaches
- Match existing async/await patterns and database transaction handling
- Preserve the project's architectural principles

**Smart Modifications:**
- Adapt the provided code to work seamlessly with existing dependencies
- Modify class initialization to match current dependency injection patterns
- Adjust database operations to use existing connection management
- Update import statements to match actual project structure

**Security Integration:**
- Integrate image validation with existing `SecurityValidator`
- Use current authentication and authorization patterns
- Apply existing rate limiting and user validation
- Follow established audit logging practices

### 4. Specific Tasks

1. **File Creation & Updates:**
   - Create new files: `bot/handlers/image_command.py`, `bot/features/image_processor.py`, `claude/image_integration.py`
   - Update existing files: `bot/core.py`, `config/settings.py`, `storage/database.py`, etc.
   - Add localization entries to translation files

2. **Database Integration:**
   - Create migration scripts compatible with existing database management
   - Add new repository methods following current repository patterns
   - Ensure proper foreign key relationships with existing tables

3. **Configuration Management:**
   - Add image settings to Pydantic configuration model
   - Include environment variable mappings
   - Set appropriate defaults for different environments

4. **Error Handling:**
   - Integrate with existing error handling systems
   - Use current logging patterns and structured logging
   - Implement proper exception hierarchy

5. **Testing Preparation:**
   - Suggest test cases for the new functionality
   - Provide integration testing scenarios
   - Include error condition testing

### 5. Expected Deliverables

**Primary Output:**
- Complete, working implementation of `/img` command integrated into existing project
- All necessary file modifications with proper diff context
- Database migration scripts ready for execution
- Updated configuration with proper validation

**Documentation:**
- Integration summary with changed files list
- Testing instructions and validation steps
- Configuration guide for deployment
- Troubleshooting guide for common issues

**Quality Assurance:**
- Code that follows existing patterns and conventions
- Proper error handling and logging
- Security validation and input sanitization
- Resource cleanup and memory management

### 6. Critical Considerations

**Security First:**
- All image uploads must go through existing security validation
- Implement proper file type validation and size limits
- Ensure safe temporary file handling and cleanup
- Validate user permissions and rate limiting

**Performance Optimization:**
- Async processing for all I/O operations
- Efficient memory usage for image processing
- Proper resource cleanup and garbage collection
- Optimized database queries and connections

**Maintainability:**
- Clear separation of concerns following existing architecture
- Comprehensive error handling and logging
- Easy configuration and feature flag management
- Documentation for future maintenance

### 7. Integration Validation

After implementation, please verify:

1. **Functional Testing:**
   - `/img` command accepts and processes images correctly
   - Batch processing works with multiple images
   - Session management handles timeouts and cleanup
   - Claude CLI integration processes images successfully

2. **Integration Testing:**
   - No conflicts with existing commands or handlers
   - Database operations work with existing schema
   - Security middleware properly validates image uploads
   - Localization works for all supported languages

3. **Error Scenarios:**
   - Invalid image formats are rejected
   - File size limits are enforced
   - Network timeouts are handled gracefully
   - Resource cleanup works under error conditions

## Files to Analyze First

Please start by examining these key files to understand the existing patterns:

1. `bot/core.py` - Bot initialization and handler registration
2. `bot/handlers/command.py` - Existing command handler patterns
3. `config/settings.py` - Configuration structure and validation
4. `storage/database.py` - Database management and migrations
5. `security/validators.py` - Security validation patterns
6. `claude/integration.py` - Claude CLI integration patterns

Then proceed with intelligent integration of the `/img` command implementation while maintaining full compatibility with the existing codebase.

## Success Criteria

The implementation is successful when:
- `/img` command works seamlessly within existing bot architecture
- All security, performance, and reliability standards are maintained
- Code follows existing patterns and is easily maintainable
- Feature can be enabled/disabled via configuration
- Comprehensive error handling and logging is in place
- Database operations are efficient and properly managed

Please analyze the codebase thoroughly and implement the `/img` command functionality with full attention to existing patterns, security requirements, and architectural consistency.