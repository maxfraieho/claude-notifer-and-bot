-- Migration: Add MCP Management System
-- Date: 2025-01-XX
-- Description: Add tables for MCP server management

-- MCP server templates table
CREATE TABLE IF NOT EXISTS mcp_server_templates (
    id SERIAL PRIMARY KEY,
    server_type VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    command_template TEXT NOT NULL,
    args_template JSON,
    env_template JSON,
    config_schema JSON,
    setup_instructions TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User MCP servers table
CREATE TABLE IF NOT EXISTS user_mcp_servers (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    server_name VARCHAR(100) NOT NULL,
    server_type VARCHAR(50) NOT NULL,
    server_command TEXT NOT NULL,
    server_args JSON,
    server_env JSON,
    config JSON,
    is_active BOOLEAN DEFAULT true,
    is_enabled BOOLEAN DEFAULT true,
    status VARCHAR(20) DEFAULT 'inactive',
    last_used TIMESTAMP,
    last_status_check TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(user_id, server_name),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (server_type) REFERENCES mcp_server_templates(server_type)
);

-- User active context table
CREATE TABLE IF NOT EXISTS user_active_context (
    user_id BIGINT PRIMARY KEY,
    selected_server VARCHAR(100),
    context_settings JSON,
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- MCP usage log table
CREATE TABLE IF NOT EXISTS mcp_usage_log (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    server_name VARCHAR(100),
    query TEXT,
    response_time INTEGER,
    success BOOLEAN,
    error_message TEXT,
    cost REAL DEFAULT 0.0,
    session_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_mcp_servers_user_id ON user_mcp_servers(user_id);
CREATE INDEX IF NOT EXISTS idx_user_mcp_servers_status ON user_mcp_servers(status);
CREATE INDEX IF NOT EXISTS idx_user_mcp_servers_type ON user_mcp_servers(server_type);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_log_user_id ON mcp_usage_log(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_log_created_at ON mcp_usage_log(created_at);

-- Insert default server templates
INSERT INTO mcp_server_templates (server_type, display_name, description, command_template, args_template, env_template, config_schema, setup_instructions) VALUES
('github', 'GitHub Integration', 'Доступ до GitHub репозиторіїв, issues, pull requests та іншого', 'npx', '["-y", "@modelcontextprotocol/server-github"]', '{"GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_token}"}', '{"type": "object", "properties": {"github_token": {"type": "string", "description": "GitHub Personal Access Token", "required": true}}}', '1. Перейдіть до GitHub Settings > Developer settings > Personal access tokens\n2. Створіть новий токен з доступом до репозиторіїв\n3. Скопіюйте токен'),

('filesystem', 'File System Access', 'Читання та запис файлів у вказаних директоріях', 'npx', '["-y", "@modelcontextprotocol/server-filesystem", "${config:allowed_path}"]', '{}', '{"type": "object", "properties": {"allowed_path": {"type": "string", "description": "Шлях до дозволеної директорії", "required": true}}}', 'Вкажіть повний шлях до директорії, де Claude може читати/писати файли'),

('postgres', 'PostgreSQL Database', 'Запити та управління PostgreSQL базами даних', 'npx', '["-y", "@modelcontextprotocol/server-postgres", "${config:connection_string}"]', '{}', '{"type": "object", "properties": {"connection_string": {"type": "string", "description": "Рядок підключення PostgreSQL", "required": true}}}', 'Формат: postgresql://username:password@host:port/database'),

('sqlite', 'SQLite Database', 'Запити та управління SQLite базами даних', 'npx', '["-y", "@modelcontextprotocol/server-sqlite", "${config:database_path}"]', '{}', '{"type": "object", "properties": {"database_path": {"type": "string", "description": "Шлях до файлу SQLite бази даних", "required": true}}}', 'Вкажіть повний шлях до файлу вашої SQLite бази даних'),

('git', 'Git Repository Tools', 'Git операції та управління репозиторіями', 'uvx', '["mcp-server-git", "--repository", "${config:repo_path}"]', '{}', '{"type": "object", "properties": {"repo_path": {"type": "string", "description": "Шлях до git репозиторію", "required": true}}}', 'Вкажіть шлях до вашого git репозиторію'),

('playwright', 'Web Automation', 'Автоматизація браузера та веб-скрапінг', 'npx', '["-y", "@modelcontextprotocol/server-playwright"]', '{}', '{"type": "object", "properties": {}}', 'Додаткова конфігурація не потрібна')

ON CONFLICT (server_type) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    command_template = EXCLUDED.command_template,
    args_template = EXCLUDED.args_template,
    env_template = EXCLUDED.env_template,
    config_schema = EXCLUDED.config_schema,
    setup_instructions = EXCLUDED.setup_instructions;
