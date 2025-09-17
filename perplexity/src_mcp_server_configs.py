"""MCP Server Configuration Templates.

Predefined configurations for popular MCP servers with setup wizards.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import structlog

from .exceptions import MCPValidationError

logger = structlog.get_logger()


class ServerConfigTemplate:
    """Base class for MCP server configuration templates."""

    def __init__(self, server_type: str, display_name: str, description: str):
        self.server_type = server_type
        self.display_name = display_name
        self.description = description

    def get_setup_steps(self) -> List[Dict[str, Any]]:
        """Get interactive setup steps."""
        raise NotImplementedError

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate configuration parameters."""
        raise NotImplementedError

    def build_server_config(self, user_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build final server configuration from user inputs."""
        raise NotImplementedError


class GitHubServerTemplate(ServerConfigTemplate):
    """GitHub MCP server template."""

    def __init__(self):
        super().__init__(
            server_type="github",
            display_name="🐙 GitHub Integration",
            description="Доступ до GitHub репозиторіїв, issues, pull requests та іншого"
        )

    def get_setup_steps(self) -> List[Dict[str, Any]]:
        """Get GitHub setup steps."""
        return [
            {
                "step": 1,
                "title": "GitHub Personal Access Token",
                "description": "Вам потрібен GitHub Personal Access Token для доступу до API",
                "input_type": "password",
                "input_key": "github_token",
                "placeholder": "ghp_xxxxxxxxxxxxxxxxxx",
                "validation": "required",
                "help_text": (
                    "Як отримати токен:\n"
                    "1. Перейдіть до GitHub.com\n"
                    "2. Settings → Developer settings → Personal access tokens → Tokens (classic)\n"
                    "3. Generate new token (classic)\n"
                    "4. Виберіть scopes: repo, read:user\n"
                    "5. Скопіюйте згенерований токен"
                )
            },
            {
                "step": 2,
                "title": "Назва сервера",
                "description": "Введіть назву для цього MCP сервера",
                "input_type": "text",
                "input_key": "server_name",
                "placeholder": "github-main",
                "validation": "required",
                "default": "github"
            }
        ]

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate GitHub configuration."""
        if not config.get("github_token"):
            return False, "GitHub токен є обов'язковим"

        token = config["github_token"].strip()
        if not token.startswith("ghp_") and not token.startswith("github_pat_") and not token.startswith("gho_"):
            return False, "Невірний формат GitHub токену"

        if len(token) < 20:
            return False, "GitHub токен занадто короткий"

        return True, None

    def build_server_config(self, user_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build GitHub server configuration."""
        return {
            "name": user_inputs.get("server_name", "github"),
            "server_type": "github",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": user_inputs["github_token"]
            },
            "config": {
                "github_token": user_inputs["github_token"]  # Store for reference
            }
        }


class FilesystemServerTemplate(ServerConfigTemplate):
    """Filesystem MCP server template."""

    def __init__(self):
        super().__init__(
            server_type="filesystem",
            display_name="📁 File System Access",
            description="Читання та запис файлів у вказаних директоріях"
        )

    def get_setup_steps(self) -> List[Dict[str, Any]]:
        """Get filesystem setup steps."""
        return [
            {
                "step": 1,
                "title": "Дозволена директорія",
                "description": "Вкажіть шлях до директорії, де Claude може працювати з файлами",
                "input_type": "text",
                "input_key": "allowed_path",
                "placeholder": "/home/user/projects",
                "validation": "required",
                "help_text": (
                    "Важливо:\n"
                    "• Вкажіть повний абсолютний шлях\n"
                    "• Переконайтеся, що директорія існує\n"
                    "• Claude матиме доступ тільки до цієї директорії\n"
                    "• Приклад: /home/username/my-project"
                )
            },
            {
                "step": 2,
                "title": "Назва сервера",
                "description": "Введіть назву для цього MCP сервера",
                "input_type": "text",
                "input_key": "server_name",
                "placeholder": "filesystem-project",
                "validation": "required",
                "default": "filesystem"
            }
        ]

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate filesystem configuration."""
        allowed_path = config.get("allowed_path", "").strip()
        if not allowed_path:
            return False, "Шлях до директорії є обов'язковим"

        if not allowed_path.startswith("/"):
            return False, "Шлях повинен бути абсолютним (починатися з /)"

        # Basic path validation
        if ".." in allowed_path:
            return False, "Шлях не може містити '..' для безпеки"

        return True, None

    def build_server_config(self, user_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build filesystem server configuration."""
        return {
            "name": user_inputs.get("server_name", "filesystem"),
            "server_type": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", user_inputs["allowed_path"]],
            "env": {},
            "config": {
                "allowed_path": user_inputs["allowed_path"]
            }
        }


class PostgresServerTemplate(ServerConfigTemplate):
    """PostgreSQL MCP server template."""

    def __init__(self):
        super().__init__(
            server_type="postgres",
            display_name="🐘 PostgreSQL Database",
            description="Запити та управління PostgreSQL базами даних"
        )

    def get_setup_steps(self) -> List[Dict[str, Any]]:
        """Get PostgreSQL setup steps."""
        return [
            {
                "step": 1,
                "title": "Connection String",
                "description": "Введіть рядок підключення до PostgreSQL бази даних",
                "input_type": "password",
                "input_key": "connection_string",
                "placeholder": "postgresql://user:password@localhost:5432/dbname",
                "validation": "required",
                "help_text": (
                    "Формат: postgresql://username:password@host:port/database\n\n"
                    "Приклади:\n"
                    "• postgresql://user:pass@localhost:5432/mydb\n"
                    "• postgresql://user:pass@host.com:5432/prod_db\n\n"
                    "Переконайтеся, що база даних доступна та користувач має необхідні права"
                )
            },
            {
                "step": 2,
                "title": "Назва сервера",
                "description": "Введіть назву для цього MCP сервера",
                "input_type": "text",
                "input_key": "server_name",
                "placeholder": "postgres-main",
                "validation": "required",
                "default": "postgres"
            }
        ]

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate PostgreSQL configuration."""
        connection_string = config.get("connection_string", "").strip()
        if not connection_string:
            return False, "Connection string є обов'язковим"

        if not connection_string.startswith("postgresql://"):
            return False, "Connection string повинен починатися з postgresql://"

        # Basic format validation
        if "@" not in connection_string or "/" not in connection_string:
            return False, "Невірний формат connection string"

        return True, None

    def build_server_config(self, user_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build PostgreSQL server configuration."""
        return {
            "name": user_inputs.get("server_name", "postgres"),
            "server_type": "postgres",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", user_inputs["connection_string"]],
            "env": {},
            "config": {
                "connection_string": user_inputs["connection_string"]
            }
        }


class SQLiteServerTemplate(ServerConfigTemplate):
    """SQLite MCP server template."""

    def __init__(self):
        super().__init__(
            server_type="sqlite",
            display_name="💾 SQLite Database",
            description="Запити та управління SQLite базами даних"
        )

    def get_setup_steps(self) -> List[Dict[str, Any]]:
        """Get SQLite setup steps."""
        return [
            {
                "step": 1,
                "title": "Шлях до БД файлу",
                "description": "Введіть повний шлях до SQLite файлу бази даних",
                "input_type": "text",
                "input_key": "database_path",
                "placeholder": "/path/to/database.db",
                "validation": "required",
                "help_text": (
                    "Вкажіть повний шлях до .db файлу:\n"
                    "• /home/user/data/app.db\n"
                    "• /var/lib/myapp/database.sqlite\n\n"
                    "Файл повинен існувати та бути доступним для читання"
                )
            },
            {
                "step": 2,
                "title": "Назва сервера",
                "description": "Введіть назву для цього MCP сервера",
                "input_type": "text",
                "input_key": "server_name",
                "placeholder": "sqlite-app",
                "validation": "required",
                "default": "sqlite"
            }
        ]

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate SQLite configuration."""
        database_path = config.get("database_path", "").strip()
        if not database_path:
            return False, "Шлях до бази даних є обов'язковим"

        if not database_path.startswith("/"):
            return False, "Шлях повинен бути абсолютним (починатися з /)"

        if not (database_path.endswith(".db") or database_path.endswith(".sqlite") or 
                database_path.endswith(".sqlite3")):
            return False, "Файл повинен мати розширення .db, .sqlite або .sqlite3"

        return True, None

    def build_server_config(self, user_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build SQLite server configuration."""
        return {
            "name": user_inputs.get("server_name", "sqlite"),
            "server_type": "sqlite",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sqlite", user_inputs["database_path"]],
            "env": {},
            "config": {
                "database_path": user_inputs["database_path"]
            }
        }


class GitServerTemplate(ServerConfigTemplate):
    """Git MCP server template."""

    def __init__(self):
        super().__init__(
            server_type="git",
            display_name="🔧 Git Repository Tools",
            description="Git операції та управління репозиторіями"
        )

    def get_setup_steps(self) -> List[Dict[str, Any]]:
        """Get Git setup steps."""
        return [
            {
                "step": 1,
                "title": "Шлях до репозиторію",
                "description": "Введіть шлях до git репозиторію",
                "input_type": "text",
                "input_key": "repo_path",
                "placeholder": "/path/to/git/repo",
                "validation": "required",
                "help_text": (
                    "Вкажіть шлях до директорії з git репозиторієм:\n"
                    "• /home/user/my-project\n"
                    "• /var/www/website\n\n"
                    "Директорія повинна містити .git папку"
                )
            },
            {
                "step": 2,
                "title": "Назва сервера",
                "description": "Введіть назву для цього MCP сервера",
                "input_type": "text",
                "input_key": "server_name",
                "placeholder": "git-project",
                "validation": "required",
                "default": "git"
            }
        ]

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate Git configuration."""
        repo_path = config.get("repo_path", "").strip()
        if not repo_path:
            return False, "Шлях до репозиторію є обов'язковим"

        if not repo_path.startswith("/"):
            return False, "Шлях повинен бути абсолютним (починатися з /)"

        return True, None

    def build_server_config(self, user_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build Git server configuration."""
        return {
            "name": user_inputs.get("server_name", "git"),
            "server_type": "git",
            "command": "uvx",
            "args": ["mcp-server-git", "--repository", user_inputs["repo_path"]],
            "env": {},
            "config": {
                "repo_path": user_inputs["repo_path"]
            }
        }


class PlaywrightServerTemplate(ServerConfigTemplate):
    """Playwright MCP server template."""

    def __init__(self):
        super().__init__(
            server_type="playwright",
            display_name="🌐 Web Automation",
            description="Автоматизація браузера та веб-скрапінг"
        )

    def get_setup_steps(self) -> List[Dict[str, Any]]:
        """Get Playwright setup steps."""
        return [
            {
                "step": 1,
                "title": "Назва сервера",
                "description": "Введіть назву для цього MCP сервера",
                "input_type": "text",
                "input_key": "server_name",
                "placeholder": "playwright-web",
                "validation": "required",
                "default": "playwright",
                "help_text": (
                    "Playwright MCP сервер не потребує додаткової конфігурації.\n"
                    "Він надає можливості автоматизації браузера та веб-скрапінгу."
                )
            }
        ]

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate Playwright configuration."""
        return True, None  # No special validation needed

    def build_server_config(self, user_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build Playwright server configuration."""
        return {
            "name": user_inputs.get("server_name", "playwright"),
            "server_type": "playwright",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-playwright"],
            "env": {},
            "config": {}
        }


class ServerConfigRegistry:
    """Registry of available MCP server configuration templates."""

    def __init__(self):
        self.templates = {
            "github": GitHubServerTemplate(),
            "filesystem": FilesystemServerTemplate(),
            "postgres": PostgresServerTemplate(),
            "sqlite": SQLiteServerTemplate(),
            "git": GitServerTemplate(),
            "playwright": PlaywrightServerTemplate(),
        }

    def get_template(self, server_type: str) -> Optional[ServerConfigTemplate]:
        """Get template by server type."""
        return self.templates.get(server_type)

    def get_all_templates(self) -> Dict[str, ServerConfigTemplate]:
        """Get all available templates."""
        return self.templates.copy()

    def get_template_list(self) -> List[Dict[str, str]]:
        """Get list of templates for display."""
        return [
            {
                "server_type": server_type,
                "display_name": template.display_name,
                "description": template.description
            }
            for server_type, template in self.templates.items()
        ]


# Global registry instance
server_config_registry = ServerConfigRegistry()
