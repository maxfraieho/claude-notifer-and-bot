"""DRACON-YAML System for Telegram Bot Logic Modeling.

This module implements DRACON (Дружелюбные Русские Алгоритмы, Которые Обеспечивают Надежность)
language for modeling bot process logic using "silhouette" schemas (closed graphs) stored in YAML.

Features:
- YAML-based DRACON schema definition and validation
- Intelligent graph analysis using Claude CLI integration
- Automatic component generation (buttons, commands, messages, handlers)
- Graph closure verification and logical integrity checks
- Visual logic modeling with closed graph topology
"""

import asyncio
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import structlog
import yaml
from pydantic import BaseModel, Field, validator

logger = structlog.get_logger()


class NodeType(str, Enum):
    """DRACON node types."""
    START = "start"
    END = "end"
    ACTION = "action"
    CONDITION = "condition"
    PROCESS = "process"
    HANDLER = "handler"
    COMMAND = "command"
    CALLBACK = "callback"
    MESSAGE = "message"
    BUTTON = "button"


class EdgeType(str, Enum):
    """DRACON edge types."""
    SEQUENCE = "sequence"
    CONDITION_TRUE = "true"
    CONDITION_FALSE = "false"
    CALLBACK = "callback"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class DraconNode:
    """DRACON graph node."""
    id: str
    type: NodeType
    name: str
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Tuple[int, int]] = None


@dataclass
class DraconEdge:
    """DRACON graph edge."""
    id: str
    from_node: str
    to_node: str
    type: EdgeType
    condition: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


class DraconSchema(BaseModel):
    """DRACON schema validation model."""

    class Config:
        extra = "forbid"

    version: str = Field(default="1.0")
    name: str = Field(..., description="Schema name")
    description: Optional[str] = Field(None, description="Schema description")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    nodes: List[Dict[str, Any]] = Field(..., description="Graph nodes")
    edges: List[Dict[str, Any]] = Field(..., description="Graph edges")

    @validator('nodes')
    def validate_nodes(cls, v):
        """Validate nodes structure."""
        if not v:
            raise ValueError("At least one node is required")

        node_ids = set()
        has_start = False
        has_end = False

        for node in v:
            if 'id' not in node:
                raise ValueError("Node must have 'id' field")
            if 'type' not in node:
                raise ValueError("Node must have 'type' field")
            if 'name' not in node:
                raise ValueError("Node must have 'name' field")

            node_id = node['id']
            if node_id in node_ids:
                raise ValueError(f"Duplicate node ID: {node_id}")
            node_ids.add(node_id)

            node_type = node['type']
            if node_type not in [t.value for t in NodeType]:
                raise ValueError(f"Invalid node type: {node_type}")

            if node_type == NodeType.START:
                has_start = True
            elif node_type == NodeType.END:
                has_end = True

        if not has_start:
            raise ValueError("Graph must have at least one START node")
        if not has_end:
            raise ValueError("Graph must have at least one END node")

        return v

    @validator('edges')
    def validate_edges(cls, v, values):
        """Validate edges structure and references."""
        if 'nodes' not in values:
            return v

        node_ids = {node['id'] for node in values['nodes']}
        edge_ids = set()

        for edge in v:
            if 'id' not in edge:
                raise ValueError("Edge must have 'id' field")
            if 'from_node' not in edge:
                raise ValueError("Edge must have 'from_node' field")
            if 'to_node' not in edge:
                raise ValueError("Edge must have 'to_node' field")
            if 'type' not in edge:
                raise ValueError("Edge must have 'type' field")

            edge_id = edge['id']
            if edge_id in edge_ids:
                raise ValueError(f"Duplicate edge ID: {edge_id}")
            edge_ids.add(edge_id)

            from_node = edge['from_node']
            to_node = edge['to_node']

            if from_node not in node_ids:
                raise ValueError(f"Edge references unknown from_node: {from_node}")
            if to_node not in node_ids:
                raise ValueError(f"Edge references unknown to_node: {to_node}")

            edge_type = edge['type']
            if edge_type not in [t.value for t in EdgeType]:
                raise ValueError(f"Invalid edge type: {edge_type}")

        return v


@dataclass
class GraphAnalysisResult:
    """Result of DRACON graph analysis."""
    is_valid: bool
    is_closed: bool
    is_reachable: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    claude_analysis: Optional[str] = None
    components: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ComponentSpec:
    """Generated component specification."""
    type: str
    name: str
    code: str
    properties: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


class DraconYamlProcessor:
    """DRACON-YAML processor for bot logic modeling."""

    def __init__(self, claude_cli_path: str = "claude"):
        """Initialize processor."""
        self.claude_cli_path = claude_cli_path
        self.logger = logger.bind(component="dracon_yaml")

    def load_schema(self, yaml_content: str) -> DraconSchema:
        """Load and validate DRACON schema from YAML."""
        try:
            data = yaml.safe_load(yaml_content)
            schema = DraconSchema(**data)
            self.logger.info("DRACON schema loaded", name=schema.name)
            return schema
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            raise ValueError(f"Schema validation failed: {e}")

    def parse_graph(self, schema: DraconSchema) -> Tuple[List[DraconNode], List[DraconEdge]]:
        """Parse schema into graph structures."""
        nodes = []
        edges = []

        for node_data in schema.nodes:
            node = DraconNode(
                id=node_data['id'],
                type=NodeType(node_data['type']),
                name=node_data['name'],
                description=node_data.get('description'),
                properties=node_data.get('properties', {}),
                position=tuple(node_data['position']) if 'position' in node_data else None
            )
            nodes.append(node)

        for edge_data in schema.edges:
            edge = DraconEdge(
                id=edge_data['id'],
                from_node=edge_data['from_node'],
                to_node=edge_data['to_node'],
                type=EdgeType(edge_data['type']),
                condition=edge_data.get('condition'),
                properties=edge_data.get('properties', {})
            )
            edges.append(edge)

        return nodes, edges

    def verify_graph_closure(self, nodes: List[DraconNode], edges: List[DraconEdge]) -> Tuple[bool, List[str]]:
        """Verify that graph forms a closed silhouette (no intersecting lines)."""
        issues = []

        # Build adjacency graph
        node_map = {node.id: node for node in nodes}
        adjacency = {node.id: [] for node in nodes}

        for edge in edges:
            adjacency[edge.from_node].append(edge.to_node)

        # Check for unreachable nodes
        start_nodes = [node for node in nodes if node.type == NodeType.START]
        if not start_nodes:
            issues.append("No START node found")
            return False, issues

        visited = set()
        queue = [start_nodes[0].id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(adjacency[current])

        unreachable = set(node_map.keys()) - visited
        if unreachable:
            issues.append(f"Unreachable nodes: {', '.join(unreachable)}")

        # Check for cycles (should be controlled cycles only)
        def has_uncontrolled_cycles():
            color = {node.id: 'white' for node in nodes}

            def dfs(node_id):
                if color[node_id] == 'gray':
                    return True  # Back edge found (cycle)
                if color[node_id] == 'black':
                    return False

                color[node_id] = 'gray'
                for neighbor in adjacency[node_id]:
                    if dfs(neighbor):
                        return True
                color[node_id] = 'black'
                return False

            for node in nodes:
                if color[node.id] == 'white':
                    if dfs(node.id):
                        return True
            return False

        # Check for proper termination
        end_nodes = [node for node in nodes if node.type == NodeType.END]
        if not end_nodes:
            issues.append("No END node found")

        is_closed = len(issues) == 0 and not has_uncontrolled_cycles()

        return is_closed, issues

    def check_reachability(self, nodes: List[DraconNode], edges: List[DraconEdge]) -> Tuple[bool, List[str]]:
        """Check if all END nodes are reachable from START nodes."""
        issues = []

        # Build graph
        node_map = {node.id: node for node in nodes}
        adjacency = {node.id: [] for node in nodes}

        for edge in edges:
            adjacency[edge.from_node].append(edge.to_node)

        start_nodes = [node for node in nodes if node.type == NodeType.START]
        end_nodes = [node for node in nodes if node.type == NodeType.END]

        if not start_nodes:
            issues.append("No START nodes found")
            return False, issues

        if not end_nodes:
            issues.append("No END nodes found")
            return False, issues

        # Check reachability from each START to each END
        def can_reach(start_id: str, end_id: str) -> bool:
            visited = set()
            queue = [start_id]

            while queue:
                current = queue.pop(0)
                if current == end_id:
                    return True
                if current in visited:
                    continue
                visited.add(current)
                queue.extend(adjacency[current])

            return False

        for start_node in start_nodes:
            reachable_ends = []
            for end_node in end_nodes:
                if can_reach(start_node.id, end_node.id):
                    reachable_ends.append(end_node.id)

            if not reachable_ends:
                issues.append(f"START node '{start_node.id}' cannot reach any END node")

        for end_node in end_nodes:
            reachable_from = []
            for start_node in start_nodes:
                if can_reach(start_node.id, end_node.id):
                    reachable_from.append(start_node.id)

            if not reachable_from:
                issues.append(f"END node '{end_node.id}' is not reachable from any START node")

        is_reachable = len(issues) == 0
        return is_reachable, issues

    async def analyze_with_claude(self, schema: DraconSchema, nodes: List[DraconNode], edges: List[DraconEdge]) -> str:
        """Analyze graph logic using Claude CLI."""
        try:
            # Prepare analysis prompt
            graph_description = self._generate_graph_description(schema, nodes, edges)

            prompt = f"""Analyze this DRACON bot logic graph for potential issues:

GRAPH: {schema.name}
{graph_description}

Please analyze for:
1. Logical flow consistency
2. Missing error handling paths
3. Potential infinite loops or deadlocks
4. Incomplete user interaction flows
5. Security considerations
6. Performance bottlenecks
7. Bot-specific patterns and best practices

Provide specific recommendations for improvement."""

            # Execute Claude analysis
            result = await self._execute_claude_analysis(prompt)
            return result

        except Exception as e:
            self.logger.error("Claude analysis failed", error=str(e))
            return f"Analysis failed: {str(e)}"

    def _generate_graph_description(self, schema: DraconSchema, nodes: List[DraconNode], edges: List[DraconEdge]) -> str:
        """Generate human-readable graph description."""
        description = f"Description: {schema.description}\n\n"

        description += "NODES:\n"
        for node in nodes:
            description += f"- {node.id} ({node.type.value}): {node.name}"
            if node.description:
                description += f" - {node.description}"
            if node.properties:
                description += f" [Properties: {node.properties}]"
            description += "\n"

        description += "\nEDGES (FLOW):\n"
        for edge in edges:
            description += f"- {edge.from_node} -> {edge.to_node} ({edge.type.value})"
            if edge.condition:
                description += f" [Condition: {edge.condition}]"
            if edge.properties:
                description += f" [Properties: {edge.properties}]"
            description += "\n"

        return description

    async def _execute_claude_analysis(self, prompt: str) -> str:
        """Execute Claude CLI analysis."""
        try:
            # Create temporary file for prompt
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name

            try:
                # Execute Claude CLI
                cmd = [self.claude_cli_path, 'chat', '--no-markdown']

                # Use subprocess with input
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate(input=prompt.encode())

                if process.returncode == 0:
                    return stdout.decode().strip()
                else:
                    error_msg = stderr.decode().strip()
                    self.logger.error("Claude CLI error", error=error_msg)
                    return f"Claude analysis error: {error_msg}"

            finally:
                # Clean up temp file
                os.unlink(prompt_file)

        except Exception as e:
            self.logger.error("Failed to execute Claude analysis", error=str(e))
            return f"Execution failed: {str(e)}"

    async def analyze_graph(self, yaml_content: str) -> GraphAnalysisResult:
        """Perform comprehensive graph analysis."""
        try:
            # Load and parse schema
            schema = self.load_schema(yaml_content)
            nodes, edges = self.parse_graph(schema)

            # Perform validation checks
            is_closed, closure_issues = self.verify_graph_closure(nodes, edges)
            is_reachable, reachability_issues = self.check_reachability(nodes, edges)

            issues = closure_issues + reachability_issues
            warnings = []
            suggestions = []

            # Add warnings for complex patterns
            if len(nodes) > 20:
                warnings.append("Large graph detected - consider breaking into smaller subgraphs")

            condition_nodes = [n for n in nodes if n.type == NodeType.CONDITION]
            if len(condition_nodes) > 5:
                warnings.append("Many condition nodes - ensure decision logic is clear")

            # Generate suggestions
            if not any(n.type == NodeType.HANDLER for n in nodes):
                suggestions.append("Consider adding error handler nodes for robustness")

            start_nodes = [n for n in nodes if n.type == NodeType.START]
            if len(start_nodes) > 1:
                suggestions.append("Multiple START nodes - ensure proper initialization")

            # Perform Claude analysis
            claude_analysis = await self.analyze_with_claude(schema, nodes, edges)

            # Identify potential components
            components = self._identify_components(nodes, edges)

            is_valid = is_closed and is_reachable and len(issues) == 0

            return GraphAnalysisResult(
                is_valid=is_valid,
                is_closed=is_closed,
                is_reachable=is_reachable,
                issues=issues,
                warnings=warnings,
                suggestions=suggestions,
                claude_analysis=claude_analysis,
                components=components
            )

        except Exception as e:
            self.logger.error("Graph analysis failed", error=str(e))
            return GraphAnalysisResult(
                is_valid=False,
                is_closed=False,
                is_reachable=False,
                issues=[f"Analysis failed: {str(e)}"]
            )

    def _identify_components(self, nodes: List[DraconNode], edges: List[DraconEdge]) -> Dict[str, List[str]]:
        """Identify potential bot components from graph."""
        components = {
            'commands': [],
            'handlers': [],
            'buttons': [],
            'messages': [],
            'callbacks': []
        }

        for node in nodes:
            if node.type == NodeType.COMMAND:
                components['commands'].append(node.id)
            elif node.type == NodeType.HANDLER:
                components['handlers'].append(node.id)
            elif node.type == NodeType.BUTTON:
                components['buttons'].append(node.id)
            elif node.type == NodeType.MESSAGE:
                components['messages'].append(node.id)
            elif node.type == NodeType.CALLBACK:
                components['callbacks'].append(node.id)

        return components

    async def generate_components(self, yaml_content: str, target_dir: str = "generated") -> List[ComponentSpec]:
        """Generate bot components from DRACON schema."""
        try:
            schema = self.load_schema(yaml_content)
            nodes, edges = self.parse_graph(schema)

            components = []

            # Generate command handlers
            command_nodes = [n for n in nodes if n.type == NodeType.COMMAND]
            for node in command_nodes:
                spec = await self._generate_command_handler(node, edges, schema)
                components.append(spec)

            # Generate callback handlers
            callback_nodes = [n for n in nodes if n.type == NodeType.CALLBACK]
            for node in callback_nodes:
                spec = await self._generate_callback_handler(node, edges, schema)
                components.append(spec)

            # Generate message templates
            message_nodes = [n for n in nodes if n.type == NodeType.MESSAGE]
            for node in message_nodes:
                spec = await self._generate_message_template(node, schema)
                components.append(spec)

            # Generate button configurations
            button_nodes = [n for n in nodes if n.type == NodeType.BUTTON]
            for node in button_nodes:
                spec = await self._generate_button_config(node, edges, schema)
                components.append(spec)

            self.logger.info("Generated components", count=len(components))
            return components

        except Exception as e:
            self.logger.error("Component generation failed", error=str(e))
            return []

    async def _generate_command_handler(self, node: DraconNode, edges: List[DraconEdge], schema: DraconSchema) -> ComponentSpec:
        """Generate command handler code."""
        command_name = node.properties.get('command', node.id.lower())

        code = f'''async def {node.id}_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generated handler for {node.name}."""
    try:
        user_id = update.effective_user.id
        logger.info("Command {command_name} invoked", user_id=user_id)

        # TODO: Implement {node.name} logic
        message = "{node.description or f'Executing {node.name}'}"

        await update.message.reply_text(message)

    except Exception as e:
        logger.error("Command {command_name} failed", error=str(e))
        await update.message.reply_text("❌ Command failed")
'''

        return ComponentSpec(
            type="command_handler",
            name=f"{node.id}_command",
            code=code,
            properties={
                'command': command_name,
                'description': node.description,
                'node_id': node.id
            }
        )

    async def _generate_callback_handler(self, node: DraconNode, edges: List[DraconEdge], schema: DraconSchema) -> ComponentSpec:
        """Generate callback handler code."""
        callback_data = node.properties.get('callback_data', node.id)

        code = f'''async def handle_{node.id}_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generated callback handler for {node.name}."""
    query = update.callback_query
    await query.answer()

    try:
        user_id = update.effective_user.id
        logger.info("Callback {callback_data} triggered", user_id=user_id)

        # TODO: Implement {node.name} callback logic

        await query.edit_message_text("{node.description or f'Processing {node.name}'}")

    except Exception as e:
        logger.error("Callback {callback_data} failed", error=str(e))
        await query.edit_message_text("❌ Action failed")
'''

        return ComponentSpec(
            type="callback_handler",
            name=f"handle_{node.id}_callback",
            code=code,
            properties={
                'callback_data': callback_data,
                'description': node.description,
                'node_id': node.id
            }
        )

    async def _generate_message_template(self, node: DraconNode, schema: DraconSchema) -> ComponentSpec:
        """Generate message template."""
        template = node.properties.get('template', node.description or node.name)

        code = f'''# Message template for {node.name}
MESSAGE_TEMPLATE = """{template}"""

def get_{node.id}_message(**kwargs) -> str:
    """Get formatted message for {node.name}."""
    return MESSAGE_TEMPLATE.format(**kwargs)
'''

        return ComponentSpec(
            type="message_template",
            name=f"get_{node.id}_message",
            code=code,
            properties={
                'template': template,
                'node_id': node.id
            }
        )

    async def _generate_button_config(self, node: DraconNode, edges: List[DraconEdge], schema: DraconSchema) -> ComponentSpec:
        """Generate button configuration."""
        button_text = node.properties.get('text', node.name)
        callback_data = node.properties.get('callback_data', node.id)

        # Find outgoing edges to determine button behavior
        outgoing_edges = [e for e in edges if e.from_node == node.id]

        code = f'''# Button configuration for {node.name}
BUTTON_CONFIG = {{
    "text": "{button_text}",
    "callback_data": "{callback_data}",
    "description": "{node.description or ''}",
    "node_id": "{node.id}"
}}

def create_{node.id}_button() -> InlineKeyboardButton:
    """Create {node.name} button."""
    return InlineKeyboardButton(
        BUTTON_CONFIG["text"],
        callback_data=BUTTON_CONFIG["callback_data"]
    )
'''

        return ComponentSpec(
            type="button_config",
            name=f"create_{node.id}_button",
            code=code,
            properties={
                'text': button_text,
                'callback_data': callback_data,
                'node_id': node.id,
                'outgoing_edges': len(outgoing_edges)
            }
        )


# Example DRACON schema for bot menu system
EXAMPLE_MENU_SCHEMA = """
version: "1.0"
name: "Bot Main Menu Flow"
description: "Main menu navigation flow for Telegram bot"
metadata:
  author: "DRACON Generator"
  created: "2024-01-01"

nodes:
  - id: "start"
    type: "start"
    name: "Bot Start"
    description: "User starts interaction with bot"
    position: [0, 0]

  - id: "main_menu"
    type: "message"
    name: "Main Menu"
    description: "Display main menu with options"
    position: [100, 0]
    properties:
      template: "🏠 **Main Menu**\\n\\nChoose an action:"

  - id: "help_button"
    type: "button"
    name: "Help Button"
    description: "Get help information"
    position: [200, -50]
    properties:
      text: "❓ Help"
      callback_data: "help"

  - id: "settings_button"
    type: "button"
    name: "Settings Button"
    description: "Open settings"
    position: [200, 50]
    properties:
      text: "⚙️ Settings"
      callback_data: "settings"

  - id: "help_handler"
    type: "callback"
    name: "Help Handler"
    description: "Process help request"
    position: [300, -50]
    properties:
      callback_data: "help"

  - id: "settings_handler"
    type: "callback"
    name: "Settings Handler"
    description: "Process settings request"
    position: [300, 50]
    properties:
      callback_data: "settings"

  - id: "help_message"
    type: "message"
    name: "Help Message"
    description: "Display help information"
    position: [400, -50]
    properties:
      template: "❓ **Help**\\n\\nAvailable commands:\\n/start - Start bot\\n/help - Show help"

  - id: "settings_message"
    type: "message"
    name: "Settings Message"
    description: "Display settings"
    position: [400, 50]
    properties:
      template: "⚙️ **Settings**\\n\\nLanguage: English\\nNotifications: On"

  - id: "end"
    type: "end"
    name: "End"
    description: "User interaction complete"
    position: [500, 0]

edges:
  - id: "start_to_menu"
    from_node: "start"
    to_node: "main_menu"
    type: "sequence"

  - id: "menu_to_help_btn"
    from_node: "main_menu"
    to_node: "help_button"
    type: "sequence"

  - id: "menu_to_settings_btn"
    from_node: "main_menu"
    to_node: "settings_button"
    type: "sequence"

  - id: "help_btn_to_handler"
    from_node: "help_button"
    to_node: "help_handler"
    type: "callback"

  - id: "settings_btn_to_handler"
    from_node: "settings_button"
    to_node: "settings_handler"
    type: "callback"

  - id: "help_handler_to_message"
    from_node: "help_handler"
    to_node: "help_message"
    type: "sequence"

  - id: "settings_handler_to_message"
    from_node: "settings_handler"
    to_node: "settings_message"
    type: "sequence"

  - id: "help_to_end"
    from_node: "help_message"
    to_node: "end"
    type: "sequence"

  - id: "settings_to_end"
    from_node: "settings_message"
    to_node: "end"
    type: "sequence"
"""