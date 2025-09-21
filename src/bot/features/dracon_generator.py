"""
DRACON Code Generator - Automatic Python Code Generation

This module generates Python code from DRACON schemas with support for
Telegram bot handlers, state machines, and complete application frameworks.
"""

import ast
import inspect
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from jinja2 import Environment, BaseLoader, Template
from dataclasses import asdict
import logging
from datetime import datetime

from dracon_types import (
    DraconSchema, DraconNode, DraconEdge, NodeType, EdgeType,
    BotHandlerInfo, CodeGenerationResult
)

logger = logging.getLogger(__name__)


class DraconCodeGenerator:
    """Main code generator for DRACON schemas"""

    def __init__(self):
        self.analyzer = None

    def generate_telegram_bot(self, schema: DraconSchema) -> CodeGenerationResult:
        """Generate complete Telegram bot from DRACON schema"""
        try:
            # Analyze schema
            self.analyzer = DraconCodeAnalyzer(schema)
            analysis = self.analyzer.analyze()

            # Generate code files
            files = {}
            errors = []
            warnings = []

            # Main bot file
            bot_code = self._generate_bot_file(analysis)
            files[f"{analysis['bot_metadata']['bot_name'].lower()}.py"] = bot_code

            # Configuration file
            config_code = self._generate_config_file(analysis)
            files['config.py'] = config_code

            # Main entry point
            main_code = self._generate_main_file(analysis)
            files['main.py'] = main_code

            # Requirements file
            requirements_code = self._generate_requirements_file(analysis)
            files['requirements.txt'] = requirements_code

            success = len(errors) == 0
            return CodeGenerationResult(
                success=success,
                generated_code=bot_code,
                files=files,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return CodeGenerationResult(
                success=False,
                errors=[f"Code generation error: {str(e)}"]
            )

    def _generate_bot_file(self, analysis: Dict[str, Any]) -> str:
        """Generate main bot file"""
        bot_name = analysis['bot_metadata']['bot_class_name']
        metadata = analysis['schema_metadata']
        handlers = analysis['handlers']

        # Generate handler implementations
        handler_code = []
        for handler in handlers:
            impl = self._generate_handler_implementation(handler, analysis)
            handler_code.append(impl)

        bot_template = f""""""
{metadata['description']}

Generated from DRACON schema: {metadata['name']}
Author: {metadata['author']}
Version: {metadata['version']}
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, ContextTypes, filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class {bot_name}:
    """{metadata['description']}"""

    def __init__(self, token: str):
        self.token = token
        self.application = None
        self.current_states = {{}}  # user_id -> current_node_id
        self.session_data = {{}}    # user_id -> session_data

    async def initialize(self):
        """Initialize the bot application"""
        self.application = Application.builder().token(self.token).build()

        # Register handlers
        {self._generate_handler_registrations(handlers)}

        logger.info("Bot initialized successfully")

    async def start(self):
        """Start the bot"""
        if not self.application:
            await self.initialize()

        logger.info("Starting bot...")
        await self.application.run_polling()

    async def stop(self):
        """Stop the bot"""
        if self.application:
            await self.application.stop()
            logger.info("Bot stopped")

    def get_user_state(self, user_id: int) -> Optional[str]:
        """Get current state for user"""
        return self.current_states.get(user_id)

    def set_user_state(self, user_id: int, node_id: str):
        """Set current state for user"""
        self.current_states[user_id] = node_id
        logger.debug(f"User {{user_id}} state changed to {{node_id}}")

    def get_session_data(self, user_id: int) -> Dict[str, Any]:
        """Get session data for user"""
        return self.session_data.get(user_id, {{}})

    def update_session_data(self, user_id: int, data: Dict[str, Any]):
        """Update session data for user"""
        if user_id not in self.session_data:
            self.session_data[user_id] = {{}}
        self.session_data[user_id].update(data)

{chr(10).join(handler_code)}


async def main():
    """Main entry point"""
    import os

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return

    bot = {bot_name}(token)

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await bot.stop()


if __name__ == '__main__':
    asyncio.run(main())
"""

        return bot_template

    def _generate_handler_registrations(self, handlers: List[BotHandlerInfo]) -> str:
        """Generate handler registration code"""
        registrations = []
        for handler in handlers:
            if handler.handler_type == "command":
                registrations.append(f"        self.application.add_handler(CommandHandler('{handler.command_name}', self.{handler.name}))")
            elif handler.handler_type == "callback":
                registrations.append(f"        self.application.add_handler(CallbackQueryHandler(self.{handler.name}, pattern=r'^{handler.callback_data}.*'))")
            elif handler.handler_type == "message":
                registrations.append(f"        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.{handler.name}))")

        return "\n".join(registrations)

    def _generate_handler_implementation(self, handler: BotHandlerInfo, analysis: Dict[str, Any]) -> str:
        """Generate implementation for a specific handler"""
        # Find corresponding node
        node = None
        for n in self.analyzer.schema.nodes:
            if n.id == handler.dracon_node_id:
                node = n
                break

        if not node:
            return f"    # Handler for {handler.name} - node not found"

        # Find next nodes
        next_edges = [e for e in self.analyzer.schema.edges if e.from_node == node.id]
        next_node = next_edges[0].to_node if next_edges else None

        handler_template = f"""    async def {handler.name}(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """{handler.description}"""
        user_id = update.effective_user.id

        try:
            # Get current state and session data
            current_state = self.get_user_state(user_id)
            session_data = self.get_session_data(user_id)

            {self._generate_node_logic(node, next_node, next_edges)}

        except Exception as e:
            logger.error(f"Error in {handler.name}: {{e}}")
            await update.effective_message.reply_text(
                "An error occurred. Please try again later."
            )
"""

        return handler_template

    def _generate_node_logic(self, node: DraconNode, next_node: Optional[str], edges: List[DraconEdge]) -> str:
        """Generate logic for different node types"""
        text = node.properties.get('text', '')

        if node.node_type == NodeType.TITLE:
            logic = f"""# Title node - entry point
            await update.effective_message.reply_text(
                "{text}",
                parse_mode='HTML'
            )"""
            if next_node:
                logic += f"\n            self.set_user_state(user_id, '{next_node}')"

        elif node.node_type == NodeType.ACTION:
            logic = f"""# Action node - perform action
            logger.info(f"User {{user_id}} performed action: {text}")
            await update.effective_message.reply_text("Action completed: {text}")"""
            if next_node:
                logic += f"\n            self.set_user_state(user_id, '{next_node}')"

        elif node.node_type == NodeType.QUESTION:
            choices = []
            for edge in edges:
                choices.append(f"[InlineKeyboardButton('{edge.label or 'Option'}', callback_data='choice_{node.id}_{edge.to_node}')]")

            logic = f"""# Question node - present choice
            keyboard = [
                {(',\n                '.join(choices))}
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                "{text}",
                reply_markup=reply_markup
            )"""

        elif node.node_type == NodeType.END:
            logic = f"""# End node - cleanup
            if user_id in self.current_states:
                del self.current_states[user_id]
            if user_id in self.session_data:
                del self.session_data[user_id]

            await update.effective_message.reply_text("{text or 'Session completed!'}")"""

        else:
            logic = f"""# Default node logic
            await update.effective_message.reply_text("{text}")"""
            if next_node:
                logic += f"\n            self.set_user_state(user_id, '{next_node}')"

        return logic

    def _generate_config_file(self, analysis: Dict[str, Any]) -> str:
        """Generate configuration file"""
        bot_name = analysis['bot_metadata']['bot_name']

        return f""""""
Configuration module for {bot_name}
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class BotConfig:
    """Bot configuration settings"""
    token: str
    debug: bool = False
    log_level: str = "INFO"
    session_timeout: int = 3600  # 1 hour
    max_concurrent_users: int = 1000

    @classmethod
    def from_environment(cls) -> 'BotConfig':
        """Create config from environment variables"""
        return cls(
            token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '3600')),
            max_concurrent_users=int(os.getenv('MAX_CONCURRENT_USERS', '1000')),
        )


# Default configuration
config = BotConfig.from_environment()
"""

    def _generate_main_file(self, analysis: Dict[str, Any]) -> str:
        """Generate main entry point file"""
        bot_name = analysis['bot_metadata']['bot_name']
        bot_class = analysis['bot_metadata']['bot_class_name']
        bot_module = bot_name.lower()

        return f"""#!/usr/bin/env python3
"""
{bot_name} - Generated DRACON Telegram Bot

This bot was automatically generated from a DRACON schema.
Generated on: {datetime.now().isoformat()}
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from {bot_module} import {bot_class}


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


async def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)

    # Get bot token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
        logger.info("Set it using: export TELEGRAM_BOT_TOKEN='your-bot-token'")
        return 1

    # Create and start bot
    bot = {bot_class}(token)

    try:
        logger.info("Starting {bot_name}...")
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {{e}}")
        return 1
    finally:
        await bot.stop()

    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
"""

    def _generate_requirements_file(self, analysis: Dict[str, Any]) -> str:
        """Generate requirements.txt file"""
        bot_name = analysis['bot_metadata']['bot_name']

        return f"""# Requirements for {bot_name}
# Generated from DRACON schema

# Core dependencies
python-telegram-bot>=22.0
asyncio
typing
dataclasses
pathlib
datetime
enum

# Development dependencies (optional)
pytest>=7.0
black>=22.0
flake8>=5.0
mypy>=1.0
"""


class DraconCodeAnalyzer:
    """Analyzer for DRACON schemas to extract code generation patterns"""

    def __init__(self, schema: DraconSchema):
        self.schema = schema
        self.handlers = []
        self.states = []
        self.transitions = []

    def analyze(self) -> Dict[str, Any]:
        """Analyze schema and extract code generation data"""
        # Find entry points
        entry_nodes = self._find_entry_nodes()

        # Analyze nodes for handler generation
        for node in self.schema.nodes:
            handler_info = self._analyze_node(node)
            if handler_info:
                self.handlers.append(handler_info)

        # Analyze workflow patterns
        workflow_patterns = self._analyze_workflow_patterns()

        # Extract bot metadata
        bot_metadata = self._extract_bot_metadata()

        return {
            'handlers': self.handlers,
            'entry_nodes': entry_nodes,
            'workflow_patterns': workflow_patterns,
            'bot_metadata': bot_metadata,
            'schema_metadata': asdict(self.schema.metadata)
        }

    def _find_entry_nodes(self) -> List[str]:
        """Find entry point nodes (nodes with no incoming edges)"""
        incoming_nodes = {edge.to_node for edge in self.schema.edges}
        all_nodes = {node.id for node in self.schema.nodes}
        return list(all_nodes - incoming_nodes)

    def _analyze_node(self, node: DraconNode) -> Optional[BotHandlerInfo]:
        """Analyze a node to determine handler requirements"""
        if node.node_type == NodeType.TITLE:
            return BotHandlerInfo(
                name=f"handle_{node.id}",
                handler_type="command",
                command_name="start",
                description=node.properties.get('text', 'Entry point'),
                dracon_node_id=node.id
            )

        elif node.node_type == NodeType.ACTION:
            # Check if this is a command handler
            text = node.properties.get('text', '')
            if text.startswith('/'):
                command_name = text[1:].split()[0]
                return BotHandlerInfo(
                    name=f"handle_{command_name}",
                    handler_type="command", 
                    command_name=command_name,
                    description=f"Handle {command_name} command",
                    dracon_node_id=node.id
                )
            else:
                return BotHandlerInfo(
                    name=f"action_{node.id}",
                    handler_type="message",
                    description=f"Handle action: {text[:50]}",
                    dracon_node_id=node.id
                )

        elif node.node_type == NodeType.QUESTION:
            return BotHandlerInfo(
                name=f"question_{node.id}",
                handler_type="callback",
                callback_data=f"q_{node.id}",
                description=f"Handle question: {node.properties.get('text', '')[:50]}",
                dracon_node_id=node.id
            )

        elif node.node_type == NodeType.CASE:
            return BotHandlerInfo(
                name=f"case_{node.id}",
                handler_type="callback",
                callback_data=f"c_{node.id}",
                description=f"Handle case logic",
                dracon_node_id=node.id
            )

        return None

    def _analyze_workflow_patterns(self) -> Dict[str, Any]:
        """Analyze workflow patterns for code generation"""
        patterns = {
            'has_state_machine': len(self.schema.edges) > 2,
            'has_conditional_logic': any(
                node.node_type in [NodeType.QUESTION, NodeType.CASE] 
                for node in self.schema.nodes
            ),
            'has_loops': any(
                edge.edge_type == EdgeType.LOOP_BACK 
                for edge in self.schema.edges
            ),
            'complexity_score': self._calculate_complexity()
        }
        return patterns

    def _calculate_complexity(self) -> int:
        """Calculate schema complexity score"""
        score = 0
        score += len(self.schema.nodes)
        score += len(self.schema.edges) * 0.5
        score += len(self.schema.macros) * 2

        # Add complexity for special node types
        for node in self.schema.nodes:
            if node.node_type in [NodeType.QUESTION, NodeType.CASE]:
                score += 2
            elif node.node_type == NodeType.LOOP_START:
                score += 3

        return int(score)

    def _extract_bot_metadata(self) -> Dict[str, Any]:
        """Extract bot-specific metadata"""
        return {
            'bot_name': self.schema.metadata.name.replace(' ', ''),
            'bot_class_name': self._to_class_name(self.schema.metadata.name),
            'description': self.schema.metadata.description,
            'version': self.schema.metadata.version
        }

    def _to_class_name(self, name: str) -> str:
        """Convert name to valid Python class name"""
        # Remove special characters and convert to PascalCase
        words = ''.join(c if c.isalnum() else ' ' for c in name).split()
        return ''.join(word.capitalize() for word in words if word) + 'Bot'


# Utility functions

def generate_bot_from_schema_file(schema_file: Path, output_dir: Path) -> CodeGenerationResult:
    """Generate bot code from schema file"""
    from dracon_parser import DraconParser

    # Parse schema
    parser = DraconParser()
    parse_result = parser.parse_file(schema_file)

    if not parse_result.success:
        return CodeGenerationResult(
            success=False,
            errors=parse_result.errors
        )

    # Generate code
    generator = DraconCodeGenerator()
    result = generator.generate_telegram_bot(parse_result.schema)

    if result.success:
        # Save files to output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in result.files.items():
            file_path = output_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        logger.info(f"Generated bot files in {output_dir}")

    return result


def validate_generated_code(code: str) -> List[str]:
    """Validate generated Python code"""
    errors = []

    try:
        # Parse the code to check syntax
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")

    return errors
