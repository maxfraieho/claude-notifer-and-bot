"""Enhanced DRACON-YAML System with Professional Components.

This module integrates Perplexity's enterprise-grade DRACON implementation
with our existing Telegram bot logic modeling system.

Features:
- Professional DRACON parser with DRAKON Hub compatibility
- Visual SVG/PNG diagram generation
- Enhanced code generation with Jinja2 templates
- Complete type system with validation
- Intelligent graph analysis using Claude CLI integration
- Visual logic modeling with closed graph topology
"""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import io

import structlog
import yaml

# Import enhanced DRACON components from Perplexity
from .dracon_types import (
    DraconSchema, DraconNode, DraconEdge, NodeType, EdgeType,
    Position, Size, SchemaMetadata, CanvasProperties, ValidationRules,
    ParseResult, DraconMetadata, VisualProperties, RenderOptions,
    CodeGenerationResult
)
from .dracon_parser import DraconParser
from .dracon_renderer import DraconRenderer
from .dracon_generator import DraconCodeGenerator

logger = structlog.get_logger()


class EnhancedDraconProcessor:
    """Enhanced DRACON processor combining our bot integration with Perplexity's professional components."""

    def __init__(self):
        """Initialize enhanced DRACON processor with Perplexity components."""
        self.parser = DraconParser()
        self.renderer = DraconRenderer()
        self.generator = DraconCodeGenerator()

    async def process_schema_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a DRACON schema file with enhanced capabilities."""
        try:
            # Parse with professional parser
            parse_result = self.parser.parse_file(file_path)

            if not parse_result.success:
                return {
                    "success": False,
                    "errors": parse_result.errors,
                    "warnings": parse_result.warnings
                }

            schema = parse_result.schema

            # Generate analysis report
            analysis = await self._analyze_schema(schema)

            # Generate visual diagram
            svg_diagram = await self._generate_diagram(schema)

            # Generate bot components
            components = await self._generate_components(schema)

            return {
                "success": True,
                "schema": schema,
                "analysis": analysis,
                "svg_diagram": svg_diagram,
                "components": components,
                "metadata": {
                    "name": schema.metadata.name,
                    "version": schema.metadata.version,
                    "node_count": len(schema.nodes),
                    "edge_count": len(schema.edges),
                    "complexity": self._calculate_complexity(schema)
                }
            }

        except Exception as e:
            logger.error("Schema processing failed", error=str(e), file_path=str(file_path))
            return {
                "success": False,
                "errors": [f"Processing failed: {str(e)}"]
            }

    async def _analyze_schema(self, schema: DraconSchema) -> Dict[str, Any]:
        """Analyze schema using Claude CLI integration."""
        analysis_prompt = f"""
Analyze this DRACON schema for bot logic:

Schema: {schema.metadata.name}
Nodes: {len(schema.nodes)}
Edges: {len(schema.edges)}

Node details:
{self._format_nodes_for_analysis(schema.nodes)}

Edge details:
{self._format_edges_for_analysis(schema.edges)}

Provide analysis on:
1. Logic flow completeness
2. Potential deadlocks or infinite loops
3. Missing error handling paths
4. Optimization suggestions
5. Bot-specific recommendations

Format as JSON with fields: completeness, deadlocks, error_handling, optimizations, recommendations
"""

        try:
            # Use Claude CLI for intelligent analysis
            result = await self._call_claude_cli(analysis_prompt)
            if result and result.get('success'):
                try:
                    return json.loads(result['output'])
                except json.JSONDecodeError:
                    return {"analysis": result['output']}

            return {"analysis": "Analysis not available"}

        except Exception as e:
            logger.warning("Schema analysis failed", error=str(e))
            return {"analysis": f"Analysis failed: {str(e)}"}

    async def _generate_diagram(self, schema: DraconSchema) -> Optional[str]:
        """Generate SVG diagram using professional renderer."""
        try:
            options = RenderOptions(
                format="svg",
                theme="default",
                width=1200,
                height=800,
                show_grid=True,
                show_labels=True
            )

            svg_content = self.renderer.render(schema, options)
            return svg_content

        except Exception as e:
            logger.error("Diagram generation failed", error=str(e))
            return None

    async def _generate_components(self, schema: DraconSchema) -> Dict[str, Any]:
        """Generate bot components from schema."""
        try:
            # Generate complete bot code
            generation_result = self.generator.generate_telegram_bot(schema)

            if not generation_result.success:
                return {
                    "success": False,
                    "errors": generation_result.errors
                }

            # Extract components
            components = {
                "handlers": self._extract_handlers(schema),
                "commands": self._extract_commands(schema),
                "callbacks": self._extract_callbacks(schema),
                "messages": self._extract_messages(schema),
                "buttons": self._extract_buttons(schema),
                "generated_code": generation_result.generated_code,
                "files": generation_result.files
            }

            return {
                "success": True,
                "components": components
            }

        except Exception as e:
            logger.error("Component generation failed", error=str(e))
            return {
                "success": False,
                "errors": [f"Component generation failed: {str(e)}"]
            }

    def _extract_handlers(self, schema: DraconSchema) -> List[Dict[str, Any]]:
        """Extract handler information from schema."""
        handlers = []

        for node in schema.nodes:
            if node.node_type in [NodeType.ACTION, NodeType.QUESTION]:
                handlers.append({
                    "id": node.id,
                    "type": node.node_type.value,
                    "name": node.properties.get("text", f"Handler {node.id}"),
                    "description": node.properties.get("description", ""),
                    "position": [node.position.x, node.position.y]
                })

        return handlers

    def _extract_commands(self, schema: DraconSchema) -> List[Dict[str, Any]]:
        """Extract command information from schema."""
        commands = []

        for node in schema.nodes:
            if node.node_type == NodeType.TITLE:
                commands.append({
                    "id": node.id,
                    "command": node.properties.get("command", "start"),
                    "description": node.properties.get("text", "Start command"),
                    "handler": f"handle_{node.id}"
                })

        return commands

    def _extract_callbacks(self, schema: DraconSchema) -> List[Dict[str, Any]]:
        """Extract callback information from schema."""
        callbacks = []

        for edge in schema.edges:
            if edge.edge_type == EdgeType.TRUE or edge.edge_type == EdgeType.FALSE:
                if edge.condition:
                    callbacks.append({
                        "id": edge.id,
                        "callback_data": edge.condition,
                        "from_node": edge.from_node,
                        "to_node": edge.to_node,
                        "handler": f"callback_{edge.id}"
                    })

        return callbacks

    def _extract_messages(self, schema: DraconSchema) -> List[Dict[str, Any]]:
        """Extract message information from schema."""
        messages = []

        for node in schema.nodes:
            if node.properties.get("template"):
                messages.append({
                    "id": node.id,
                    "template": node.properties["template"],
                    "type": node.node_type.value,
                    "variables": self._extract_variables(node.properties["template"])
                })

        return messages

    def _extract_buttons(self, schema: DraconSchema) -> List[Dict[str, Any]]:
        """Extract button information from schema."""
        buttons = []

        for node in schema.nodes:
            if node.properties.get("text") and node.properties.get("callback_data"):
                buttons.append({
                    "id": node.id,
                    "text": node.properties["text"],
                    "callback_data": node.properties["callback_data"],
                    "type": "inline"
                })

        return buttons

    def _extract_variables(self, template: str) -> List[str]:
        """Extract variables from message template."""
        import re
        return re.findall(r'\{(\w+)\}', template)

    def _calculate_complexity(self, schema: DraconSchema) -> int:
        """Calculate schema complexity score."""
        base_score = len(schema.nodes) + len(schema.edges)

        # Add complexity for different node types
        for node in schema.nodes:
            if node.node_type == NodeType.QUESTION:
                base_score += 2  # Decisions add complexity
            elif node.node_type in [NodeType.LOOP_START, NodeType.LOOP_END]:
                base_score += 3  # Loops add more complexity

        return min(base_score, 100)  # Cap at 100

    def _format_nodes_for_analysis(self, nodes: List[DraconNode]) -> str:
        """Format nodes for Claude analysis."""
        formatted = []
        for node in nodes:
            formatted.append(f"- {node.id} ({node.node_type.value}): {node.properties.get('text', 'No description')}")
        return "\n".join(formatted)

    def _format_edges_for_analysis(self, edges: List[DraconEdge]) -> str:
        """Format edges for Claude analysis."""
        formatted = []
        for edge in edges:
            condition = f" [{edge.condition}]" if edge.condition else ""
            formatted.append(f"- {edge.from_node} -> {edge.to_node} ({edge.edge_type.value}){condition}")
        return "\n".join(formatted)

    async def _call_claude_cli(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Claude CLI for analysis."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                temp_file = f.name

            # Call Claude CLI
            process = await asyncio.create_subprocess_exec(
                'claude', 'chat', '--no-markdown',
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout, stderr = await process.communicate(input=prompt.encode())

            if process.returncode == 0:
                return {
                    "success": True,
                    "output": stdout.decode().strip()
                }
            else:
                logger.error("Claude CLI failed", stderr=stderr.decode())
                return {
                    "success": False,
                    "error": stderr.decode()
                }

        except Exception as e:
            logger.error("Claude CLI call failed", error=str(e))
            return None
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.debug("Failed to clean up temporary file", temp_file=temp_file, error=str(e))
                pass


async def create_example_schema() -> DraconSchema:
    """Create an example DRACON schema for demonstration."""
    metadata = SchemaMetadata(
        name="Enhanced Bot Example",
        version="1.0.0",
        description="Example bot with enhanced DRACON features",
        author="Enhanced DRACON System"
    )

    schema = DraconSchema(metadata=metadata)

    # Add start node
    start_node = DraconNode(
        id="start",
        node_type=NodeType.TITLE,
        position=Position(x=100, y=100),
        size=Size(width=120, height=60),
        properties={
            "text": "🚀 Welcome to Enhanced Bot!",
            "command": "start"
        }
    )
    schema.add_node(start_node)

    # Add menu node
    menu_node = DraconNode(
        id="main_menu",
        node_type=NodeType.ACTION,
        position=Position(x=300, y=100),
        size=Size(width=140, height=80),
        properties={
            "text": "Main Menu",
            "template": "🏠 **Main Menu**\n\nChoose an option:"
        }
    )
    schema.add_node(menu_node)

    # Add end node
    end_node = DraconNode(
        id="end",
        node_type=NodeType.END,
        position=Position(x=500, y=100),
        size=Size(width=100, height=50),
        properties={
            "text": "End"
        }
    )
    schema.add_node(end_node)

    # Add edges
    start_edge = DraconEdge(
        id="start_to_menu",
        from_node="start",
        to_node="main_menu",
        edge_type=EdgeType.SEQUENCE
    )
    schema.add_edge(start_edge)

    menu_edge = DraconEdge(
        id="menu_to_end",
        from_node="main_menu",
        to_node="end",
        edge_type=EdgeType.SEQUENCE
    )
    schema.add_edge(menu_edge)

    return schema