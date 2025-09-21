"""DRACON Reverse Engineering: Convert Bot Code to DRACON Schemas.

This module analyzes existing Telegram bot code and converts it into
DRACON-YAML schemas for visualization and modernization.

Features:
- AST parsing of Python bot handlers
- Logic flow detection and mapping
- Intelligent code analysis with Claude
- Automatic DRACON schema generation
- Refactoring recommendations
"""

import ast
import inspect
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import structlog
import yaml

from .dracon_yaml import DraconSchema, NodeType, EdgeType

logger = structlog.get_logger()


@dataclass
class HandlerInfo:
    """Information about a bot handler function."""
    name: str
    function_name: str
    file_path: str
    line_number: int
    handler_type: str  # 'command', 'callback', 'message'
    command_name: Optional[str] = None
    callback_data: Optional[str] = None
    docstring: Optional[str] = None
    calls_functions: Set[str] = field(default_factory=set)
    sends_messages: List[str] = field(default_factory=list)
    creates_buttons: List[Dict[str, str]] = field(default_factory=list)
    has_error_handling: bool = False
    complexity_score: int = 0


@dataclass
class LogicFlow:
    """Represents a logical flow between handlers."""
    from_handler: str
    to_handler: str
    trigger_type: str  # 'command', 'callback', 'condition'
    trigger_value: Optional[str] = None
    condition: Optional[str] = None


@dataclass
class BotArchitecture:
    """Complete bot architecture analysis."""
    handlers: List[HandlerInfo]
    flows: List[LogicFlow]
    entry_points: List[str]
    orphaned_handlers: List[str]
    complexity_metrics: Dict[str, Any]
    claude_analysis: Optional[str] = None


class DraconReverseEngineer:
    """Reverse engineer bot code into DRACON schemas."""

    def __init__(self, project_root: str, claude_integration=None):
        """Initialize reverse engineer."""
        self.project_root = Path(project_root)
        self.claude_integration = claude_integration
        self.logger = logger.bind(component="dracon_reverse")

    async def analyze_bot_architecture(self, focus_path: Optional[str] = None) -> BotArchitecture:
        """Analyze complete bot architecture and extract logical flows."""
        self.logger.info("Starting bot architecture analysis")

        # Determine analysis scope
        analysis_path = Path(focus_path) if focus_path else self.project_root / "src" / "bot"

        if not analysis_path.exists():
            raise ValueError(f"Analysis path does not exist: {analysis_path}")

        # Find and analyze all Python files
        handlers = await self._discover_handlers(analysis_path)
        flows = await self._analyze_logic_flows(handlers)

        # Analyze architecture patterns
        entry_points = self._find_entry_points(handlers)
        orphaned_handlers = self._find_orphaned_handlers(handlers, flows)
        complexity_metrics = self._calculate_complexity_metrics(handlers, flows)

        # Get Claude analysis if available
        claude_analysis = None
        if self.claude_integration:
            claude_analysis = await self._get_claude_architecture_analysis(handlers, flows)

        return BotArchitecture(
            handlers=handlers,
            flows=flows,
            entry_points=entry_points,
            orphaned_handlers=orphaned_handlers,
            complexity_metrics=complexity_metrics,
            claude_analysis=claude_analysis
        )

    async def _discover_handlers(self, analysis_path: Path) -> List[HandlerInfo]:
        """Discover all bot handlers in the codebase."""
        handlers = []

        for py_file in analysis_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse AST
                tree = ast.parse(content)
                file_handlers = self._extract_handlers_from_ast(tree, py_file, content)
                handlers.extend(file_handlers)

            except Exception as e:
                self.logger.warning("Failed to parse file", file=str(py_file), error=str(e))

        self.logger.info("Discovered handlers", count=len(handlers))
        return handlers

    def _extract_handlers_from_ast(self, tree: ast.AST, file_path: Path, content: str) -> List[HandlerInfo]:
        """Extract handler information from AST."""
        handlers = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                handler_info = self._analyze_function_node(node, file_path, content)
                if handler_info:
                    handlers.append(handler_info)

        return handlers

    def _analyze_function_node(self, node: ast.FunctionDef, file_path: Path, content: str) -> Optional[HandlerInfo]:
        """Analyze a function node to determine if it's a handler."""
        func_name = node.name

        # Check if function looks like a handler
        handler_type = self._determine_handler_type(node, content)
        if not handler_type:
            return None

        # Extract handler information
        docstring = ast.get_docstring(node)
        command_name = self._extract_command_name(func_name, docstring)
        callback_data = self._extract_callback_data(node, content)

        # Analyze function body
        calls_functions = self._extract_function_calls(node)
        sends_messages = self._extract_message_sends(node)
        creates_buttons = self._extract_button_creation(node, content)
        has_error_handling = self._has_error_handling(node)
        complexity_score = self._calculate_function_complexity(node)

        return HandlerInfo(
            name=self._generate_handler_name(func_name, command_name, callback_data),
            function_name=func_name,
            file_path=str(file_path.relative_to(self.project_root)),
            line_number=node.lineno,
            handler_type=handler_type,
            command_name=command_name,
            callback_data=callback_data,
            docstring=docstring,
            calls_functions=calls_functions,
            sends_messages=sends_messages,
            creates_buttons=creates_buttons,
            has_error_handling=has_error_handling,
            complexity_score=complexity_score
        )

    def _determine_handler_type(self, node: ast.FunctionDef, content: str) -> Optional[str]:
        """Determine if function is a handler and what type."""
        func_name = node.name.lower()

        # Check function parameters for handler signature
        params = [arg.arg for arg in node.args.args]
        if not ('update' in params and 'context' in params):
            return None

        # Determine type based on name patterns
        if any(pattern in func_name for pattern in ['command', 'cmd', 'handler']):
            return 'command'
        elif any(pattern in func_name for pattern in ['callback', 'query', 'button']):
            return 'callback'
        elif any(pattern in func_name for pattern in ['message', 'text', 'handle']):
            return 'message'
        elif func_name.endswith('_handler') or func_name.endswith('_command'):
            return 'command'

        # Check for specific patterns in docstring or content
        function_content = content[node.lineno:node.end_lineno] if hasattr(node, 'end_lineno') else ""
        if 'CommandHandler' in function_content:
            return 'command'
        elif 'CallbackQueryHandler' in function_content:
            return 'callback'
        elif 'MessageHandler' in function_content:
            return 'message'

        return 'command'  # Default assumption

    def _extract_command_name(self, func_name: str, docstring: Optional[str]) -> Optional[str]:
        """Extract command name from function name or docstring."""
        # Try to extract from function name
        if func_name.endswith('_command'):
            return func_name[:-8]  # Remove '_command'
        elif func_name.endswith('_handler'):
            return func_name[:-8]  # Remove '_handler'

        # Try to extract from docstring
        if docstring:
            match = re.search(r'/(\w+)', docstring)
            if match:
                return match.group(1)

        # Generate from function name
        name = func_name.replace('_command', '').replace('_handler', '')
        return name if name else None

    def _extract_callback_data(self, node: ast.FunctionDef, content: str) -> Optional[str]:
        """Extract callback data pattern from function."""
        # Look for callback_data patterns in the function
        for child in ast.walk(node):
            if isinstance(child, ast.Str) and ':' in child.s:
                # Looks like callback data pattern
                return child.s
            elif isinstance(child, ast.Constant) and isinstance(child.value, str) and ':' in child.value:
                return child.value

        return None

    def _extract_function_calls(self, node: ast.FunctionDef) -> Set[str]:
        """Extract function calls made by this handler."""
        calls = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.add(child.func.attr)

        return calls

    def _extract_message_sends(self, node: ast.FunctionDef) -> List[str]:
        """Extract message sending patterns."""
        messages = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and child.func.attr == 'reply_text':
                    # Try to extract message content
                    if child.args and isinstance(child.args[0], (ast.Str, ast.Constant)):
                        content = child.args[0].s if isinstance(child.args[0], ast.Str) else child.args[0].value
                        if isinstance(content, str):
                            messages.append(content[:100])  # Truncate for brevity

        return messages

    def _extract_button_creation(self, node: ast.FunctionDef, content: str) -> List[Dict[str, str]]:
        """Extract inline keyboard button creation."""
        buttons = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == 'InlineKeyboardButton':
                    button_info = {}
                    if len(child.args) >= 2:
                        # Text and callback_data
                        if isinstance(child.args[0], (ast.Str, ast.Constant)):
                            text = child.args[0].s if isinstance(child.args[0], ast.Str) else child.args[0].value
                            button_info['text'] = text

                        # Check for callback_data in keyword arguments
                        for keyword in child.keywords:
                            if keyword.arg == 'callback_data':
                                if isinstance(keyword.value, (ast.Str, ast.Constant)):
                                    callback = keyword.value.s if isinstance(keyword.value, ast.Str) else keyword.value.value
                                    button_info['callback_data'] = callback

                    if button_info:
                        buttons.append(button_info)

        return buttons

    def _has_error_handling(self, node: ast.FunctionDef) -> bool:
        """Check if function has error handling."""
        for child in ast.walk(node):
            if isinstance(child, (ast.Try, ast.ExceptHandler)):
                return True
        return False

    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate complexity score for function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1

        return complexity

    def _generate_handler_name(self, func_name: str, command_name: Optional[str], callback_data: Optional[str]) -> str:
        """Generate a descriptive name for the handler."""
        if command_name:
            return f"Command: /{command_name}"
        elif callback_data:
            return f"Callback: {callback_data}"
        else:
            return f"Handler: {func_name}"

    async def _analyze_logic_flows(self, handlers: List[HandlerInfo]) -> List[LogicFlow]:
        """Analyze logical flows between handlers."""
        flows = []

        # Create mapping of callback_data to handlers
        callback_map = {}
        for handler in handlers:
            if handler.callback_data:
                callback_map[handler.callback_data] = handler

        # Analyze each handler for flows to other handlers
        for handler in handlers:
            # Check buttons created by this handler
            for button in handler.creates_buttons:
                callback_data = button.get('callback_data')
                if callback_data and callback_data in callback_map:
                    target_handler = callback_map[callback_data]
                    flows.append(LogicFlow(
                        from_handler=handler.name,
                        to_handler=target_handler.name,
                        trigger_type='callback',
                        trigger_value=callback_data
                    ))

            # Check function calls that might lead to other handlers
            for func_call in handler.calls_functions:
                target_handler = next((h for h in handlers if h.function_name == func_call), None)
                if target_handler:
                    flows.append(LogicFlow(
                        from_handler=handler.name,
                        to_handler=target_handler.name,
                        trigger_type='function_call',
                        trigger_value=func_call
                    ))

        self.logger.info("Analyzed logic flows", count=len(flows))
        return flows

    def _find_entry_points(self, handlers: List[HandlerInfo]) -> List[str]:
        """Find entry point handlers (commands that start workflows)."""
        entry_points = []

        for handler in handlers:
            if handler.handler_type == 'command' and handler.command_name in ['start', 'help', 'new']:
                entry_points.append(handler.name)
            elif handler.handler_type == 'command':
                entry_points.append(handler.name)

        return entry_points

    def _find_orphaned_handlers(self, handlers: List[HandlerInfo], flows: List[LogicFlow]) -> List[str]:
        """Find handlers that are not reachable from any entry point."""
        reachable = set()
        targets = {flow.to_handler for flow in flows}

        # Find handlers that are referenced but might not be reachable
        all_handler_names = {h.name for h in handlers}
        orphaned = all_handler_names - targets

        return list(orphaned)

    def _calculate_complexity_metrics(self, handlers: List[HandlerInfo], flows: List[LogicFlow]) -> Dict[str, Any]:
        """Calculate various complexity metrics."""
        total_handlers = len(handlers)
        total_flows = len(flows)
        avg_complexity = sum(h.complexity_score for h in handlers) / total_handlers if total_handlers > 0 else 0

        handler_types = {}
        for handler in handlers:
            handler_types[handler.handler_type] = handler_types.get(handler.handler_type, 0) + 1

        return {
            'total_handlers': total_handlers,
            'total_flows': total_flows,
            'average_complexity': round(avg_complexity, 2),
            'handler_types': handler_types,
            'has_error_handling': sum(1 for h in handlers if h.has_error_handling),
            'complexity_distribution': {
                'simple': sum(1 for h in handlers if h.complexity_score <= 3),
                'medium': sum(1 for h in handlers if 3 < h.complexity_score <= 6),
                'complex': sum(1 for h in handlers if h.complexity_score > 6)
            }
        }

    async def _get_claude_architecture_analysis(self, handlers: List[HandlerInfo], flows: List[LogicFlow]) -> str:
        """Get Claude analysis of the bot architecture."""
        try:
            # Prepare analysis prompt
            analysis_text = self._generate_architecture_description(handlers, flows)

            prompt = f"""Analyze this Telegram bot architecture and provide recommendations:

{analysis_text}

Please provide:
1. Architecture quality assessment
2. Design pattern analysis
3. Potential issues and bottlenecks
4. Modernization recommendations
5. DRACON schema conversion suggestions
6. Refactoring priorities

Focus on logical flow, maintainability, and bot-specific best practices."""

            # Execute Claude analysis (assuming we have integration)
            if hasattr(self.claude_integration, 'send_message'):
                response = await self.claude_integration.send_message(prompt)
                return response
            else:
                return "Claude analysis not available"

        except Exception as e:
            self.logger.error("Claude architecture analysis failed", error=str(e))
            return f"Analysis failed: {str(e)}"

    def _generate_architecture_description(self, handlers: List[HandlerInfo], flows: List[LogicFlow]) -> str:
        """Generate human-readable architecture description."""
        description = f"BOT ARCHITECTURE ANALYSIS\n\n"

        description += f"HANDLERS ({len(handlers)}):\n"
        for handler in handlers:
            description += f"- {handler.name} ({handler.handler_type})\n"
            description += f"  File: {handler.file_path}:{handler.line_number}\n"
            description += f"  Complexity: {handler.complexity_score}\n"
            if handler.creates_buttons:
                description += f"  Buttons: {len(handler.creates_buttons)}\n"
            if handler.docstring:
                description += f"  Purpose: {handler.docstring[:100]}...\n"
            description += "\n"

        description += f"LOGICAL FLOWS ({len(flows)}):\n"
        for flow in flows:
            description += f"- {flow.from_handler} -> {flow.to_handler}\n"
            description += f"  Trigger: {flow.trigger_type}"
            if flow.trigger_value:
                description += f" ({flow.trigger_value})"
            description += "\n"

        return description

    async def generate_dracon_schema(self, architecture: BotArchitecture, schema_name: str = "Bot Architecture") -> str:
        """Generate DRACON schema from analyzed architecture."""
        self.logger.info("Generating DRACON schema from architecture")

        # Build nodes
        nodes = []
        node_id_map = {}

        # Add start node
        nodes.append({
            'id': 'start',
            'type': 'start',
            'name': 'Bot Start',
            'description': 'User interaction begins',
            'position': [0, 0]
        })

        # Add handler nodes
        for i, handler in enumerate(architecture.handlers):
            node_id = f"handler_{i}"
            node_id_map[handler.name] = node_id

            # Determine node type
            node_type = 'command' if handler.handler_type == 'command' else 'callback'
            if handler.handler_type == 'message':
                node_type = 'process'

            nodes.append({
                'id': node_id,
                'type': node_type,
                'name': handler.name,
                'description': handler.docstring or f"Handler: {handler.function_name}",
                'position': [100 + (i % 5) * 150, 100 + (i // 5) * 100],
                'properties': {
                    'function_name': handler.function_name,
                    'file_path': handler.file_path,
                    'complexity': handler.complexity_score,
                    'command_name': handler.command_name,
                    'callback_data': handler.callback_data
                }
            })

        # Add end node
        nodes.append({
            'id': 'end',
            'type': 'end',
            'name': 'Interaction Complete',
            'description': 'User interaction ends',
            'position': [500, 200]
        })

        # Build edges
        edges = []
        edge_counter = 0

        # Connect start to entry points
        for entry_point in architecture.entry_points:
            if entry_point in node_id_map:
                edges.append({
                    'id': f"edge_{edge_counter}",
                    'from_node': 'start',
                    'to_node': node_id_map[entry_point],
                    'type': 'sequence'
                })
                edge_counter += 1

        # Add flow edges
        for flow in architecture.flows:
            if flow.from_handler in node_id_map and flow.to_handler in node_id_map:
                edge_type = 'callback' if flow.trigger_type == 'callback' else 'sequence'

                edges.append({
                    'id': f"edge_{edge_counter}",
                    'from_node': node_id_map[flow.from_handler],
                    'to_node': node_id_map[flow.to_handler],
                    'type': edge_type,
                    'properties': {
                        'trigger_type': flow.trigger_type,
                        'trigger_value': flow.trigger_value
                    }
                })
                edge_counter += 1

        # Connect orphaned handlers to end (temporary solution)
        for handler in architecture.handlers:
            handler_id = node_id_map.get(handler.name)
            if handler_id and not any(edge['to_node'] == handler_id for edge in edges if edge['to_node'] != 'start'):
                edges.append({
                    'id': f"edge_{edge_counter}",
                    'from_node': handler_id,
                    'to_node': 'end',
                    'type': 'sequence'
                })
                edge_counter += 1

        # Build complete schema
        schema_data = {
            'version': '1.0',
            'name': schema_name,
            'description': f'Reverse-engineered DRACON schema from bot code ({len(architecture.handlers)} handlers)',
            'metadata': {
                'generated_from': 'reverse_engineering',
                'complexity_metrics': architecture.complexity_metrics,
                'analysis_timestamp': 'auto-generated'
            },
            'nodes': nodes,
            'edges': edges
        }

        # Convert to YAML
        yaml_content = yaml.dump(schema_data, default_flow_style=False, sort_keys=False, allow_unicode=True)

        self.logger.info("Generated DRACON schema",
                        nodes=len(nodes),
                        edges=len(edges))

        return yaml_content

    async def suggest_refactoring(self, architecture: BotArchitecture) -> Dict[str, Any]:
        """Suggest refactoring improvements based on analysis."""
        suggestions = {
            'complexity_issues': [],
            'flow_improvements': [],
            'modernization_opportunities': [],
            'architectural_patterns': []
        }

        # Analyze complexity issues
        for handler in architecture.handlers:
            if handler.complexity_score > 6:
                suggestions['complexity_issues'].append({
                    'handler': handler.name,
                    'issue': f"High complexity score: {handler.complexity_score}",
                    'recommendation': "Consider breaking into smaller functions"
                })

            if not handler.has_error_handling:
                suggestions['complexity_issues'].append({
                    'handler': handler.name,
                    'issue': "No error handling detected",
                    'recommendation': "Add try/except blocks for robustness"
                })

        # Analyze flow improvements
        if architecture.orphaned_handlers:
            suggestions['flow_improvements'].append({
                'issue': f"{len(architecture.orphaned_handlers)} orphaned handlers",
                'handlers': architecture.orphaned_handlers,
                'recommendation': "Connect orphaned handlers or remove if unused"
            })

        # Suggest modernization
        command_handlers = [h for h in architecture.handlers if h.handler_type == 'command']
        if len(command_handlers) > 10:
            suggestions['modernization_opportunities'].append({
                'opportunity': "Large number of command handlers",
                'recommendation': "Consider grouping related commands or implementing subcommands"
            })

        # Architectural patterns
        if len(architecture.flows) < len(architecture.handlers) * 0.5:
            suggestions['architectural_patterns'].append({
                'pattern': "Low interconnectivity",
                'recommendation': "Consider adding more interactive flows between handlers"
            })

        return suggestions


# Example usage functions
async def reverse_engineer_bot(project_root: str, claude_integration=None) -> Tuple[BotArchitecture, str]:
    """Reverse engineer a bot into DRACON schema."""
    engineer = DraconReverseEngineer(project_root, claude_integration)

    # Analyze architecture
    architecture = await engineer.analyze_bot_architecture()

    # Generate DRACON schema
    schema_yaml = await engineer.generate_dracon_schema(architecture)

    return architecture, schema_yaml