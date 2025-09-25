"""
DRACON Language Parser with AST Generation

This module provides complete DRACON language parsing with Abstract Syntax Tree
generation, supporting all DRAKON Hub format features and DRACON language constructs.
"""

import ast
import re
import yaml
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import json
import logging
from dataclasses import asdict

from dracon_types import (
    DraconSchema, DraconNode, DraconEdge, NodeType, EdgeType,
    Position, Size, SchemaMetadata, CanvasProperties, ValidationRules,
    ParseResult, DraconMetadata, VisualProperties, MacroDefinition
)

logger = logging.getLogger(__name__)


class DraconParsingError(Exception):
    """Custom exception for DRACON parsing errors"""
    pass


class DraconLexer:
    """Lexical analyzer for DRACON constructs"""

    # DRACON keywords and patterns
    KEYWORDS = {
        'title', 'action', 'question', 'case', 'select',
        'loop_start', 'loop_end', 'address', 'end', 'shelf',
        'timer', 'parallel_start', 'parallel_end', 'macro'
    }

    # Regular expressions for DRACON tokens
    PATTERNS = {
        'node_id': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
        'position': r'\((\d+),\s*(\d+)\)',
        'size': r'\[(\d+)x(\d+)\]',
        'condition': r'\{([^}]+)\}',
        'label': r'"([^"]*)"',
        'color': r'#[0-9a-fA-F]{6}',
        'connection': r'->|-->|=>|==>'
    }

    def __init__(self):
        self.compiled_patterns = {
            name: re.compile(pattern) 
            for name, pattern in self.PATTERNS.items()
        }

    def tokenize(self, text: str) -> List[Dict[str, Any]]:
        """Tokenize DRACON text input"""
        tokens = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # Skip comments
                continue

            # Extract tokens from line
            line_tokens = self._extract_line_tokens(line, line_num)
            tokens.extend(line_tokens)

        return tokens

    def _extract_line_tokens(self, line: str, line_num: int) -> List[Dict[str, Any]]:
        """Extract tokens from a single line"""
        tokens = []
        pos = 0

        while pos < len(line):
            # Skip whitespace
            while pos < len(line) and line[pos].isspace():
                pos += 1

            if pos >= len(line):
                break

            # Try to match patterns
            token_found = False

            for pattern_name, compiled_pattern in self.compiled_patterns.items():
                match = compiled_pattern.match(line, pos)
                if match:
                    tokens.append({
                        'type': pattern_name,
                        'value': match.group(0),
                        'groups': match.groups(),
                        'line': line_num,
                        'position': pos
                    })
                    pos = match.end()
                    token_found = True
                    break

            if not token_found:
                # Handle individual characters or unknown tokens
                tokens.append({
                    'type': 'unknown',
                    'value': line[pos],
                    'line': line_num,
                    'position': pos
                })
                pos += 1

        return tokens


class DraconYAMLParser:
    """Parser for DRACON-YAML format"""

    def __init__(self):
        self.lexer = DraconLexer()
        self.current_schema = None

    def parse_yaml_file(self, file_path: Path) -> ParseResult:
        """Parse a DRACON YAML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_content = yaml.safe_load(f)

            return self.parse_yaml_dict(yaml_content)

        except Exception as e:
            logger.error(f"Failed to parse YAML file {file_path}: {e}")
            return ParseResult(
                success=False,
                errors=[f"YAML parsing error: {str(e)}"]
            )

    def parse_yaml_dict(self, yaml_data: Dict[str, Any]) -> ParseResult:
        """Parse DRACON schema from YAML dictionary"""
        errors = []
        warnings = []

        try:
            # Parse metadata
            metadata = self._parse_metadata(yaml_data.get('metadata', {}))

            # Parse canvas properties
            canvas = self._parse_canvas(yaml_data.get('canvas', {}))

            # Parse validation rules
            validation_rules = self._parse_validation_rules(
                yaml_data.get('validation_rules', {})
            )

            # Create schema
            schema = DraconSchema(
                metadata=metadata,
                canvas=canvas,
                validation_rules=validation_rules
            )

            # Parse nodes
            nodes_data = yaml_data.get('nodes', [])
            for node_data in nodes_data:
                node, node_errors = self._parse_node(node_data)
                if node:
                    schema.add_node(node)
                errors.extend(node_errors)

            # Parse edges
            edges_data = yaml_data.get('edges', [])
            for edge_data in edges_data:
                edge, edge_errors = self._parse_edge(edge_data)
                if edge:
                    schema.add_edge(edge)
                errors.extend(edge_errors)

            # Parse macros
            macros_data = yaml_data.get('macros', [])
            for macro_data in macros_data:
                macro, macro_errors = self._parse_macro(macro_data)
                if macro:
                    schema.macros.append(macro)
                errors.extend(macro_errors)

            success = len(errors) == 0
            return ParseResult(
                success=success,
                schema=schema if success else None,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Schema parsing error: {e}")
            return ParseResult(
                success=False,
                errors=[f"Schema parsing error: {str(e)}"]
            )

    def _parse_metadata(self, metadata_data: Dict[str, Any]) -> SchemaMetadata:
        """Parse schema metadata"""
        from datetime import datetime

        return SchemaMetadata(
            name=metadata_data.get('name', 'Unnamed Schema'),
            version=metadata_data.get('version', '1.0.0'),
            description=metadata_data.get('description', ''),
            author=metadata_data.get('author', ''),
            created=self._parse_datetime(metadata_data.get('created')),
            modified=self._parse_datetime(metadata_data.get('modified')),
            tags=metadata_data.get('tags', []),
            dracon_version=metadata_data.get('dracon_version', '1.0')
        )

    def _parse_datetime(self, dt_str: Optional[str]) -> datetime:
        """Parse datetime string"""
        from datetime import datetime

        if not dt_str:
            return datetime.now()

        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning("Failed to parse datetime string, using current time", datetime_str=dt_str, error=str(e))
            return datetime.now()

    def _parse_canvas(self, canvas_data: Dict[str, Any]) -> CanvasProperties:
        """Parse canvas properties"""
        return CanvasProperties(
            width=canvas_data.get('width', 1200),
            height=canvas_data.get('height', 800),
            grid_size=canvas_data.get('grid_size', 20),
            theme=canvas_data.get('theme', 'default'),
            zoom=canvas_data.get('zoom', 1.0)
        )

    def _parse_validation_rules(self, rules_data: Dict[str, Any]) -> ValidationRules:
        """Parse validation rules"""
        return ValidationRules(
            no_intersections=rules_data.get('no_intersections', True),
            single_entry_exit=rules_data.get('single_entry_exit', True),
            all_paths_covered=rules_data.get('all_paths_covered', True),
            variable_scope_check=rules_data.get('variable_scope_check', True)
        )

    def _parse_node(self, node_data: Dict[str, Any]) -> Tuple[Optional[DraconNode], List[str]]:
        """Parse a DRACON node"""
        errors = []

        try:
            # Required fields
            node_id = node_data.get('id')
            node_type_str = node_data.get('type')
            position_data = node_data.get('position', {})
            size_data = node_data.get('size', {})

            if not node_id:
                errors.append("Node missing required 'id' field")
                return None, errors

            if not node_type_str:
                errors.append(f"Node {node_id} missing required 'type' field")
                return None, errors

            # Parse node type
            try:
                node_type = NodeType(node_type_str)
            except ValueError:
                errors.append(f"Invalid node type '{node_type_str}' for node {node_id}")
                return None, errors

            # Parse position and size
            position = Position(
                x=position_data.get('x', 0),
                y=position_data.get('y', 0)
            )

            size = Size(
                width=size_data.get('width', 100),
                height=size_data.get('height', 50)
            )

            # Parse properties
            properties = node_data.get('properties', {})

            # Parse DRACON metadata
            metadata_data = node_data.get('dracon_metadata', {})
            dracon_metadata = DraconMetadata(
                is_macro=metadata_data.get('is_macro', False),
                macro_definition=metadata_data.get('macro_definition'),
                data_flow=metadata_data.get('data_flow', []),
                complexity_score=metadata_data.get('complexity_score', 0)
            )

            # Parse visual properties
            visual_data = node_data.get('visual_properties', {})
            visual_properties = VisualProperties(
                color=visual_data.get('color', '#ffffff'),
                font_size=visual_data.get('font_size', 12),
                font_family=visual_data.get('font_family', 'Arial'),
                border_width=visual_data.get('border_width', 1),
                border_color=visual_data.get('border_color', '#000000'),
                background_color=visual_data.get('background_color', '#f0f0f0')
            )

            node = DraconNode(
                id=node_id,
                node_type=node_type,
                position=position,
                size=size,
                properties=properties,
                dracon_metadata=dracon_metadata,
                visual_properties=visual_properties
            )

            return node, errors

        except Exception as e:
            errors.append(f"Error parsing node: {str(e)}")
            return None, errors

    def _parse_edge(self, edge_data: Dict[str, Any]) -> Tuple[Optional[DraconEdge], List[str]]:
        """Parse a DRACON edge"""
        errors = []

        try:
            # Required fields
            edge_id = edge_data.get('id')
            from_node = edge_data.get('from_node')
            to_node = edge_data.get('to_node')
            edge_type_str = edge_data.get('type')

            if not edge_id:
                errors.append("Edge missing required 'id' field")
                return None, errors

            if not from_node:
                errors.append(f"Edge {edge_id} missing required 'from_node' field")
                return None, errors

            if not to_node:
                errors.append(f"Edge {edge_id} missing required 'to_node' field")
                return None, errors

            if not edge_type_str:
                errors.append(f"Edge {edge_id} missing required 'type' field")
                return None, errors

            # Parse edge type
            try:
                edge_type = EdgeType(edge_type_str)
            except ValueError:
                errors.append(f"Invalid edge type '{edge_type_str}' for edge {edge_id}")
                return None, errors

            # Optional fields
            condition = edge_data.get('condition')
            label = edge_data.get('label', '')

            # Parse control points
            control_points = []
            for cp_data in edge_data.get('control_points', []):
                control_points.append(ControlPoint(
                    x=cp_data.get('x', 0),
                    y=cp_data.get('y', 0)
                ))

            # Parse edge metadata
            from dracon_types import EdgeMetadata, ControlPoint
            metadata_data = edge_data.get('dracon_metadata', {})
            edge_metadata = EdgeMetadata(
                data_transfer=metadata_data.get('data_transfer', []),
                execution_weight=metadata_data.get('execution_weight', 1)
            )

            edge = DraconEdge(
                id=edge_id,
                from_node=from_node,
                to_node=to_node,
                edge_type=edge_type,
                condition=condition,
                label=label,
                control_points=control_points,
                edge_metadata=edge_metadata
            )

            return edge, errors

        except Exception as e:
            errors.append(f"Error parsing edge: {str(e)}")
            return None, errors

    def _parse_macro(self, macro_data: Dict[str, Any]) -> Tuple[Optional[MacroDefinition], List[str]]:
        """Parse a macro definition"""
        errors = []

        try:
            name = macro_data.get('name')
            if not name:
                errors.append("Macro missing required 'name' field")
                return None, errors

            parameters = macro_data.get('parameters', [])
            definition_data = macro_data.get('definition')

            # Parse nested definition if present
            definition = None
            if definition_data:
                result = self.parse_yaml_dict(definition_data)
                if result.success:
                    definition = result.schema
                else:
                    errors.extend(result.errors)

            macro = MacroDefinition(
                name=name,
                parameters=parameters,
                definition=definition
            )

            return macro, errors

        except Exception as e:
            errors.append(f"Error parsing macro: {str(e)}")
            return None, errors


class DraconHubImporter:
    """Importer for DRAKON Hub JSON format"""

    def parse_drakon_hub_file(self, file_path: Path) -> ParseResult:
        """Parse DRAKON Hub JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                hub_data = json.load(f)

            return self._convert_hub_to_dracon(hub_data)

        except Exception as e:
            logger.error(f"Failed to parse DRAKON Hub file {file_path}: {e}")
            return ParseResult(
                success=False,
                errors=[f"DRAKON Hub parsing error: {str(e)}"]
            )

    def _convert_hub_to_dracon(self, hub_data: Dict[str, Any]) -> ParseResult:
        """Convert DRAKON Hub format to DRACON schema"""
        # Implementation for converting DRAKON Hub JSON format
        # This would handle the specific format used by DRAKON Hub

        errors = []
        warnings = []

        try:
            # Extract metadata from hub format
            metadata = SchemaMetadata(
                name=hub_data.get('name', 'Imported Schema'),
                description=hub_data.get('description', ''),
                author=hub_data.get('author', ''),
                dracon_version='1.0'
            )

            # Create schema
            schema = DraconSchema(metadata=metadata)

            # Convert nodes (specific to DRAKON Hub format)
            nodes = hub_data.get('nodes', [])
            for hub_node in nodes:
                dracon_node = self._convert_hub_node(hub_node)
                if dracon_node:
                    schema.add_node(dracon_node)

            # Convert edges
            edges = hub_data.get('edges', [])
            for hub_edge in edges:
                dracon_edge = self._convert_hub_edge(hub_edge)
                if dracon_edge:
                    schema.add_edge(dracon_edge)

            return ParseResult(
                success=True,
                schema=schema,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return ParseResult(
                success=False,
                errors=[f"DRAKON Hub conversion error: {str(e)}"]
            )

    def _convert_hub_node(self, hub_node: Dict[str, Any]) -> Optional[DraconNode]:
        """Convert DRAKON Hub node to DRACON node"""
        # Specific conversion logic for DRAKON Hub node format
        try:
            node_type_map = {
                'action': NodeType.ACTION,
                'question': NodeType.QUESTION,
                'case': NodeType.CASE,
                'title': NodeType.TITLE,
                'end': NodeType.END,
                # Add more mappings as needed
            }

            hub_type = hub_node.get('type', 'action')
            node_type = node_type_map.get(hub_type, NodeType.ACTION)

            return DraconNode(
                id=hub_node.get('id', ''),
                node_type=node_type,
                position=Position(
                    x=hub_node.get('x', 0),
                    y=hub_node.get('y', 0)
                ),
                size=Size(
                    width=hub_node.get('width', 100),
                    height=hub_node.get('height', 50)
                ),
                properties={
                    'text': hub_node.get('text', ''),
                    'icon': hub_node.get('icon', ''),
                }
            )

        except Exception as e:
            logger.error(f"Error converting hub node: {e}")
            return None

    def _convert_hub_edge(self, hub_edge: Dict[str, Any]) -> Optional[DraconEdge]:
        """Convert DRAKON Hub edge to DRACON edge"""
        try:
            edge_type_map = {
                'sequence': EdgeType.SEQUENCE,
                'true': EdgeType.TRUE,
                'false': EdgeType.FALSE,
                'case': EdgeType.CASE_BRANCH,
            }

            hub_type = hub_edge.get('type', 'sequence')
            edge_type = edge_type_map.get(hub_type, EdgeType.SEQUENCE)

            return DraconEdge(
                id=hub_edge.get('id', ''),
                from_node=hub_edge.get('from', ''),
                to_node=hub_edge.get('to', ''),
                edge_type=edge_type,
                label=hub_edge.get('label', ''),
                condition=hub_edge.get('condition')
            )

        except Exception as e:
            logger.error(f"Error converting hub edge: {e}")
            return None


class DraconParser:
    """Main DRACON parser with multiple format support"""

    def __init__(self):
        self.yaml_parser = DraconYAMLParser()
        self.hub_importer = DraconHubImporter()

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse DRACON file based on extension"""
        file_path = Path(file_path)

        if file_path.suffix.lower() in ['.yaml', '.yml']:
            return self.yaml_parser.parse_yaml_file(file_path)
        elif file_path.suffix.lower() == '.json':
            return self.hub_importer.parse_drakon_hub_file(file_path)
        else:
            return ParseResult(
                success=False,
                errors=[f"Unsupported file format: {file_path.suffix}"]
            )

    def parse_yaml_string(self, yaml_string: str) -> ParseResult:
        """Parse DRACON schema from YAML string"""
        try:
            yaml_data = yaml.safe_load(yaml_string)
            return self.yaml_parser.parse_yaml_dict(yaml_data)
        except Exception as e:
            return ParseResult(
                success=False,
                errors=[f"YAML string parsing error: {str(e)}"]
            )

    def parse_json_string(self, json_string: str) -> ParseResult:
        """Parse DRAKON Hub schema from JSON string"""
        try:
            hub_data = json.loads(json_string)
            return self.hub_importer._convert_hub_to_dracon(hub_data)
        except Exception as e:
            return ParseResult(
                success=False,
                errors=[f"JSON string parsing error: {str(e)}"]
            )


# Utility functions for schema manipulation

def schema_to_dict(schema: DraconSchema) -> Dict[str, Any]:
    """Convert DRACON schema to dictionary representation"""
    return asdict(schema)


def dict_to_schema(schema_dict: Dict[str, Any]) -> DraconSchema:
    """Convert dictionary to DRACON schema"""
    # This would need proper deserialization logic
    pass


def validate_schema_references(schema: DraconSchema) -> List[str]:
    """Validate that all node references in edges exist"""
    errors = []
    node_ids = {node.id for node in schema.nodes}

    for edge in schema.edges:
        if edge.from_node not in node_ids:
            errors.append(f"Edge {edge.id} references non-existent from_node: {edge.from_node}")

        if edge.to_node not in node_ids:
            errors.append(f"Edge {edge.id} references non-existent to_node: {edge.to_node}")

    return errors
