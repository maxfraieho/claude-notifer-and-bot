"""
DRACON Visual Renderer - SVG/PNG Generation Engine

This module provides professional-quality visual rendering of DRACON schemas
with support for multiple output formats, themes, and layout algorithms.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import math
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import logging
from dataclasses import dataclass
import colorsys

from dracon_types import (
    DraconSchema, DraconNode, DraconEdge, NodeType, EdgeType,
    Position, Size, RenderOptions, DEFAULT_COLORS, DRACON_ICONS
)

logger = logging.getLogger(__name__)


@dataclass
class LayoutResult:
    """Result of layout algorithm"""
    nodes: Dict[str, Position]
    edges: Dict[str, List[Position]]
    bounds: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y


class DraconTheme:
    """Theme configuration for DRACON rendering"""

    def __init__(self, name: str = "default"):
        self.name = name
        self.colors = DEFAULT_COLORS.copy()
        self.fonts = {
            'default': 'Arial, sans-serif',
            'title': 'Arial Black, sans-serif',
            'code': 'Courier New, monospace'
        }
        self.styles = {
            'stroke_width': 2,
            'node_padding': 10,
            'font_size': 12,
            'grid_size': 20,
            'arrow_size': 8
        }

    def get_node_color(self, node_type: NodeType) -> str:
        """Get color for node type"""
        return self.colors.get(node_type.value, self.colors.get('action', '#7ed321'))

    def get_contrast_color(self, bg_color: str) -> str:
        """Get contrasting text color for background"""
        # Convert hex to RGB
        hex_color = bg_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        # Calculate luminance
        luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255

        return '#000000' if luminance > 0.5 else '#ffffff'


class SugiyamaLayoutAlgorithm:
    """Sugiyama algorithm for hierarchical layout"""

    def __init__(self, schema: DraconSchema):
        self.schema = schema
        self.layers = []
        self.node_positions = {}
        self.edge_paths = {}

    def calculate_layout(self) -> LayoutResult:
        """Calculate hierarchical layout using Sugiyama algorithm"""
        # Step 1: Cycle removal (if needed)
        self._remove_cycles()

        # Step 2: Layer assignment
        self._assign_layers()

        # Step 3: Crossing reduction
        self._reduce_crossings()

        # Step 4: Coordinate assignment
        self._assign_coordinates()

        # Calculate bounds
        bounds = self._calculate_bounds()

        return LayoutResult(
            nodes=self.node_positions,
            edges=self.edge_paths,
            bounds=bounds
        )

    def _remove_cycles(self):
        """Remove cycles in the graph (simplified implementation)"""
        # For DRACON schemas, cycles should be rare due to structured nature
        # This is a placeholder for more sophisticated cycle detection
        pass

    def _assign_layers(self):
        """Assign nodes to layers based on topological ordering"""
        # Find entry points (nodes with no incoming edges)
        incoming_count = {node.id: 0 for node in self.schema.nodes}

        for edge in self.schema.edges:
            incoming_count[edge.to_node] += 1

        # Start with entry points
        current_layer = [node.id for node.id, count in incoming_count.items() if count == 0]
        if not current_layer:
            # If no entry points, start with first node
            current_layer = [self.schema.nodes[0].id] if self.schema.nodes else []

        layer_index = 0
        processed = set()

        while current_layer:
            self.layers.append(current_layer.copy())
            next_layer = []

            for node_id in current_layer:
                processed.add(node_id)

                # Find all nodes that this node connects to
                for edge in self.schema.edges:
                    if edge.from_node == node_id and edge.to_node not in processed:
                        # Check if all prerequisites for target node are met
                        target_ready = True
                        for other_edge in self.schema.edges:
                            if (other_edge.to_node == edge.to_node and 
                                other_edge.from_node not in processed):
                                target_ready = False
                                break

                        if target_ready and edge.to_node not in next_layer:
                            next_layer.append(edge.to_node)

            current_layer = next_layer
            layer_index += 1

            # Safety break to prevent infinite loops
            if layer_index > len(self.schema.nodes):
                break

    def _reduce_crossings(self):
        """Reduce edge crossings between layers (simplified)"""
        # This is a simplified version - full implementation would use
        # barycenter heuristic or other crossing reduction algorithms

        for i in range(len(self.layers) - 1):
            # Calculate barycenter for each node in next layer
            layer = self.layers[i + 1]
            barycenters = {}

            for node_id in layer:
                connected_positions = []
                for edge in self.schema.edges:
                    if edge.to_node == node_id:
                        from_layer = self.layers[i]
                        if edge.from_node in from_layer:
                            connected_positions.append(from_layer.index(edge.from_node))

                if connected_positions:
                    barycenters[node_id] = sum(connected_positions) / len(connected_positions)
                else:
                    barycenters[node_id] = len(layer) / 2

            # Sort layer by barycenter
            self.layers[i + 1] = sorted(layer, key=lambda x: barycenters.get(x, 0))

    def _assign_coordinates(self):
        """Assign final coordinates to nodes"""
        layer_height = 150  # Vertical spacing between layers
        node_width = 120   # Horizontal spacing between nodes
        start_y = 50

        for layer_index, layer in enumerate(self.layers):
            y = start_y + layer_index * layer_height

            # Calculate total width needed for this layer
            total_width = len(layer) * node_width
            start_x = -total_width / 2  # Center the layer

            for node_index, node_id in enumerate(layer):
                x = start_x + node_index * node_width
                self.node_positions[node_id] = Position(x, y)

        # Calculate edge paths
        self._calculate_edge_paths()

    def _calculate_edge_paths(self):
        """Calculate paths for edges with control points"""
        for edge in self.schema.edges:
            from_pos = self.node_positions.get(edge.from_node)
            to_pos = self.node_positions.get(edge.to_node)

            if from_pos and to_pos:
                # Simple straight line for now
                # More sophisticated routing could be implemented
                self.edge_paths[edge.id] = [from_pos, to_pos]

    def _calculate_bounds(self) -> Tuple[float, float, float, float]:
        """Calculate bounding box of the layout"""
        if not self.node_positions:
            return (0, 0, 100, 100)

        x_coords = [pos.x for pos in self.node_positions.values()]
        y_coords = [pos.y for pos in self.node_positions.values()]

        margin = 100
        return (
            min(x_coords) - margin,
            min(y_coords) - margin,
            max(x_coords) + margin,
            max(y_coords) + margin
        )


class SVGRenderer:
    """SVG rendering engine for DRACON schemas"""

    def __init__(self, theme: DraconTheme = None):
        self.theme = theme or DraconTheme()
        self.svg_root = None
        self.defs = None

    def render_schema(self, schema: DraconSchema, options: RenderOptions) -> str:
        """Render DRACON schema to SVG string"""
        # Calculate layout
        layout_algorithm = SugiyamaLayoutAlgorithm(schema)
        layout = layout_algorithm.calculate_layout()

        # Create SVG root
        self._create_svg_root(layout.bounds, options)

        # Add definitions (gradients, patterns, markers)
        self._add_definitions()

        # Draw grid if enabled
        if options.show_grid:
            self._draw_grid(layout.bounds)

        # Draw edges first (so they appear behind nodes)
        for edge in schema.edges:
            self._draw_edge(edge, layout)

        # Draw nodes
        for node in schema.nodes:
            self._draw_node(node, layout, options)

        # Convert to string
        return self._svg_to_string()

    def _create_svg_root(self, bounds: Tuple[float, float, float, float], options: RenderOptions):
        """Create SVG root element"""
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y

        self.svg_root = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'width': str(options.width),
            'height': str(options.height),
            'viewBox': f'{min_x} {min_y} {width} {height}',
            'style': f'background-color: {self.theme.colors.get("background", "#ffffff")}'
        })

    def _add_definitions(self):
        """Add SVG definitions for reusable elements"""
        self.defs = ET.SubElement(self.svg_root, 'defs')

        # Arrow marker for edges
        arrow_marker = ET.SubElement(self.defs, 'marker', {
            'id': 'arrowhead',
            'markerWidth': '10',
            'markerHeight': '7',
            'refX': '9',
            'refY': '3.5',
            'orient': 'auto'
        })

        ET.SubElement(arrow_marker, 'polygon', {
            'points': '0 0, 10 3.5, 0 7',
            'fill': self.theme.colors.get('edge', '#666666')
        })

        # Node gradients
        for node_type in NodeType:
            base_color = self.theme.get_node_color(node_type)
            lighter_color = self._lighten_color(base_color, 0.3)

            gradient = ET.SubElement(self.defs, 'linearGradient', {
                'id': f'gradient-{node_type.value}',
                'x1': '0%',
                'y1': '0%',
                'x2': '0%',
                'y2': '100%'
            })

            ET.SubElement(gradient, 'stop', {
                'offset': '0%',
                'stop-color': lighter_color
            })

            ET.SubElement(gradient, 'stop', {
                'offset': '100%',
                'stop-color': base_color
            })

    def _draw_grid(self, bounds: Tuple[float, float, float, float]):
        """Draw background grid"""
        min_x, min_y, max_x, max_y = bounds
        grid_size = self.theme.styles['grid_size']

        grid_group = ET.SubElement(self.svg_root, 'g', {
            'class': 'grid',
            'opacity': '0.1'
        })

        # Vertical lines
        x = min_x - (min_x % grid_size)
        while x <= max_x:
            ET.SubElement(grid_group, 'line', {
                'x1': str(x),
                'y1': str(min_y),
                'x2': str(x),
                'y2': str(max_y),
                'stroke': '#cccccc',
                'stroke-width': '1'
            })
            x += grid_size

        # Horizontal lines
        y = min_y - (min_y % grid_size)
        while y <= max_y:
            ET.SubElement(grid_group, 'line', {
                'x1': str(min_x),
                'y1': str(y),
                'x2': str(max_x),
                'y2': str(y),
                'stroke': '#cccccc',
                'stroke-width': '1'
            })
            y += grid_size

    def _draw_node(self, node: DraconNode, layout: LayoutResult, options: RenderOptions):
        """Draw a DRACON node"""
        position = layout.nodes.get(node.id)
        if not position:
            return

        # Create node group
        node_group = ET.SubElement(self.svg_root, 'g', {
            'class': f'node node-{node.node_type.value}',
            'id': f'node-{node.id}'
        })

        # Get node styling
        base_color = self.theme.get_node_color(node.node_type)
        text_color = self.theme.get_contrast_color(base_color)

        # Draw node shape based on type
        if node.node_type == NodeType.TITLE:
            self._draw_title_node(node_group, position, node, base_color)
        elif node.node_type == NodeType.ACTION:
            self._draw_action_node(node_group, position, node, base_color)
        elif node.node_type == NodeType.QUESTION:
            self._draw_question_node(node_group, position, node, base_color)
        elif node.node_type == NodeType.CASE:
            self._draw_case_node(node_group, position, node, base_color)
        else:
            self._draw_default_node(node_group, position, node, base_color)

        # Add text if enabled
        if options.show_labels:
            text_content = node.properties.get('text', node.id)
            if text_content:
                self._add_node_text(node_group, position, text_content, text_color)

    def _draw_title_node(self, group: ET.Element, pos: Position, node: DraconNode, color: str):
        """Draw a title node (rounded rectangle)"""
        width = node.size.width
        height = node.size.height

        ET.SubElement(group, 'rect', {
            'x': str(pos.x - width/2),
            'y': str(pos.y - height/2),
            'width': str(width),
            'height': str(height),
            'rx': '10',
            'ry': '10',
            'fill': f'url(#gradient-{node.node_type.value})',
            'stroke': self.theme.colors.get('border', '#000000'),
            'stroke-width': str(self.theme.styles['stroke_width'])
        })

    def _draw_action_node(self, group: ET.Element, pos: Position, node: DraconNode, color: str):
        """Draw an action node (rectangle)"""
        width = node.size.width
        height = node.size.height

        ET.SubElement(group, 'rect', {
            'x': str(pos.x - width/2),
            'y': str(pos.y - height/2),
            'width': str(width),
            'height': str(height),
            'fill': f'url(#gradient-{node.node_type.value})',
            'stroke': self.theme.colors.get('border', '#000000'),
            'stroke-width': str(self.theme.styles['stroke_width'])
        })

    def _draw_question_node(self, group: ET.Element, pos: Position, node: DraconNode, color: str):
        """Draw a question node (diamond)"""
        width = node.size.width
        height = node.size.height

        points = f"{pos.x},{pos.y - height/2} {pos.x + width/2},{pos.y} {pos.x},{pos.y + height/2} {pos.x - width/2},{pos.y}"

        ET.SubElement(group, 'polygon', {
            'points': points,
            'fill': f'url(#gradient-{node.node_type.value})',
            'stroke': self.theme.colors.get('border', '#000000'),
            'stroke-width': str(self.theme.styles['stroke_width'])
        })

    def _draw_case_node(self, group: ET.Element, pos: Position, node: DraconNode, color: str):
        """Draw a case node (hexagon)"""
        width = node.size.width
        height = node.size.height

        # Create hexagon points
        points = []
        for i in range(6):
            angle = i * math.pi / 3
            x = pos.x + (width/2) * math.cos(angle)
            y = pos.y + (height/2) * math.sin(angle)
            points.append(f"{x},{y}")

        ET.SubElement(group, 'polygon', {
            'points': ' '.join(points),
            'fill': f'url(#gradient-{node.node_type.value})',
            'stroke': self.theme.colors.get('border', '#000000'),
            'stroke-width': str(self.theme.styles['stroke_width'])
        })

    def _draw_default_node(self, group: ET.Element, pos: Position, node: DraconNode, color: str):
        """Draw default node shape (rectangle)"""
        self._draw_action_node(group, pos, node, color)

    def _add_node_text(self, group: ET.Element, pos: Position, text: str, color: str):
        """Add text to a node"""
        # Split text into lines if too long
        max_chars_per_line = 12
        lines = []
        words = text.split()
        current_line = ""

        for word in words:
            if len(current_line + " " + word) <= max_chars_per_line:
                current_line = current_line + " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # Add text elements
        line_height = self.theme.styles['font_size'] + 2
        total_height = len(lines) * line_height
        start_y = pos.y - total_height/2 + line_height/2

        for i, line in enumerate(lines):
            ET.SubElement(group, 'text', {
                'x': str(pos.x),
                'y': str(start_y + i * line_height),
                'text-anchor': 'middle',
                'dominant-baseline': 'middle',
                'font-family': self.theme.fonts['default'],
                'font-size': str(self.theme.styles['font_size']),
                'fill': color
            }).text = line

    def _draw_edge(self, edge: DraconEdge, layout: LayoutResult):
        """Draw an edge connection"""
        path_points = layout.edges.get(edge.id, [])
        if len(path_points) < 2:
            return

        # Create edge group
        edge_group = ET.SubElement(self.svg_root, 'g', {
            'class': f'edge edge-{edge.edge_type.value}',
            'id': f'edge-{edge.id}'
        })

        # Draw path
        path_d = f"M {path_points[0].x},{path_points[0].y}"
        for point in path_points[1:]:
            path_d += f" L {point.x},{point.y}"

        # Get edge style
        stroke_color = self.theme.colors.get('edge', '#666666')
        stroke_width = self.theme.styles['stroke_width']

        # Special styling for different edge types
        if edge.edge_type == EdgeType.FALSE:
            stroke_color = '#d32f2f'
        elif edge.edge_type == EdgeType.TRUE:
            stroke_color = '#388e3c'

        path_element = ET.SubElement(edge_group, 'path', {
            'd': path_d,
            'stroke': stroke_color,
            'stroke-width': str(stroke_width),
            'fill': 'none',
            'marker-end': 'url(#arrowhead)'
        })

        # Add dashed line for conditional edges
        if edge.condition:
            path_element.set('stroke-dasharray', '5,5')

        # Add label if present
        if edge.label:
            mid_point = self._get_path_midpoint(path_points)
            ET.SubElement(edge_group, 'text', {
                'x': str(mid_point.x),
                'y': str(mid_point.y - 5),
                'text-anchor': 'middle',
                'font-family': self.theme.fonts['default'],
                'font-size': str(self.theme.styles['font_size'] - 2),
                'fill': stroke_color
            }).text = edge.label

    def _get_path_midpoint(self, points: List[Position]) -> Position:
        """Get midpoint of path"""
        if len(points) == 2:
            return Position(
                (points[0].x + points[1].x) / 2,
                (points[0].y + points[1].y) / 2
            )
        else:
            # For multi-point paths, return middle point
            mid_index = len(points) // 2
            return points[mid_index]

    def _lighten_color(self, hex_color: str, factor: float) -> str:
        """Lighten a hex color by a factor"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        # Convert to HSL, increase lightness, convert back
        h, l, s = colorsys.rgb_to_hls(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        l = min(1.0, l + factor)
        rgb_new = colorsys.hls_to_rgb(h, l, s)

        return f"#{int(rgb_new[0]*255):02x}{int(rgb_new[1]*255):02x}{int(rgb_new[2]*255):02x}"

    def _svg_to_string(self) -> str:
        """Convert SVG to formatted string"""
        rough_string = ET.tostring(self.svg_root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


class PNGRenderer:
    """PNG rendering using external tools or libraries"""

    def __init__(self, theme: DraconTheme = None):
        self.theme = theme or DraconTheme()
        self.svg_renderer = SVGRenderer(theme)

    def render_schema(self, schema: DraconSchema, options: RenderOptions) -> bytes:
        """Render DRACON schema to PNG bytes"""
        # First render to SVG
        svg_content = self.svg_renderer.render_schema(schema, options)

        # Convert SVG to PNG (requires external library like cairosvg)
        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=options.width,
                output_height=options.height
            )
            return png_bytes

        except ImportError:
            logger.warning("cairosvg not available, PNG rendering disabled")
            # Return SVG as fallback
            return svg_content.encode('utf-8')


class DraconRenderer:
    """Main DRACON rendering engine with multi-format support"""

    def __init__(self, theme_name: str = "default"):
        self.theme = DraconTheme(theme_name)
        self.svg_renderer = SVGRenderer(self.theme)
        self.png_renderer = PNGRenderer(self.theme)

    def render(self, schema: DraconSchema, options: RenderOptions) -> Any:
        """Render schema in specified format"""
        if options.format.lower() == 'svg':
            return self.svg_renderer.render_schema(schema, options)
        elif options.format.lower() == 'png':
            return self.png_renderer.render_schema(schema, options)
        else:
            raise ValueError(f"Unsupported render format: {options.format}")

    def save_to_file(self, schema: DraconSchema, output_path: Path, options: RenderOptions):
        """Render and save schema to file"""
        output_path = Path(output_path)
        rendered_content = self.render(schema, options)

        if options.format.lower() == 'svg':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered_content)
        elif options.format.lower() == 'png':
            with open(output_path, 'wb') as f:
                f.write(rendered_content)

        logger.info(f"Rendered schema saved to {output_path}")


# Theme presets
THEMES = {
    'default': DraconTheme('default'),
    'dark': DraconTheme('dark'),
    'high_contrast': DraconTheme('high_contrast'),
    'corporate': DraconTheme('corporate')
}

# Initialize theme variations
THEMES['dark'].colors.update({
    'background': '#2d2d2d',
    'border': '#ffffff',
    'edge': '#cccccc'
})

THEMES['high_contrast'].colors.update({
    'title': '#000000',
    'action': '#ffffff', 
    'question': '#ffff00',
    'case': '#ff0000',
    'background': '#ffffff',
    'border': '#000000',
    'edge': '#000000'
})
