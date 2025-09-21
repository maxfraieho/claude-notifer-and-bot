"""
DRACON Type Definitions and Data Structures

This module provides all the core type definitions and data structures
for the DRACON visual programming language implementation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
import uuid


class NodeType(Enum):
    """DRACON node types following DRAKON Hub format compatibility"""
    TITLE = "title"
    ACTION = "action" 
    QUESTION = "question"
    CASE = "case"
    SELECT = "select"
    LOOP_START = "loop_start"
    LOOP_END = "loop_end"
    ADDRESS = "address"
    END = "end"
    SHELF = "shelf"
    TIMER = "timer"
    PARALLEL_START = "parallel_start"
    PARALLEL_END = "parallel_end"


class EdgeType(Enum):
    """DRACON connection types"""
    SEQUENCE = "sequence"
    TRUE = "true"
    FALSE = "false"
    CASE_BRANCH = "case_branch"
    LOOP_BACK = "loop_back"


@dataclass
class Position:
    """2D position coordinates"""
    x: float
    y: float


@dataclass
class Size:
    """2D size dimensions"""
    width: float
    height: float


@dataclass
class DraconMetadata:
    """Metadata for DRACON schema elements"""
    is_macro: bool = False
    macro_definition: Optional[Dict[str, Any]] = None
    data_flow: List[str] = field(default_factory=list)
    complexity_score: int = 0


@dataclass
class VisualProperties:
    """Visual styling properties for DRACON elements"""
    color: str = "#ffffff"
    font_size: int = 12
    font_family: str = "Arial"
    border_width: int = 1
    border_color: str = "#000000"
    background_color: str = "#f0f0f0"


@dataclass
class DraconNode:
    """A single node in a DRACON schema"""
    id: str
    node_type: NodeType
    position: Position
    size: Size
    properties: Dict[str, Any] = field(default_factory=dict)
    dracon_metadata: DraconMetadata = field(default_factory=DraconMetadata)
    visual_properties: VisualProperties = field(default_factory=VisualProperties)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class ControlPoint:
    """Control point for edge routing"""
    x: float
    y: float


@dataclass
class EdgeMetadata:
    """Metadata for DRACON edges"""
    data_transfer: List[str] = field(default_factory=list)
    execution_weight: int = 1


@dataclass 
class DraconEdge:
    """A connection between DRACON nodes"""
    id: str
    from_node: str
    to_node: str
    edge_type: EdgeType
    condition: Optional[str] = None
    label: str = ""
    control_points: List[ControlPoint] = field(default_factory=list)
    edge_metadata: EdgeMetadata = field(default_factory=EdgeMetadata)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class MacroDefinition:
    """Definition of a reusable macro"""
    name: str
    parameters: List[str] = field(default_factory=list)
    definition: Optional['DraconSchema'] = None


@dataclass
class ValidationRules:
    """Validation rules for DRACON schema"""
    no_intersections: bool = True
    single_entry_exit: bool = True
    all_paths_covered: bool = True
    variable_scope_check: bool = True


@dataclass
class CanvasProperties:
    """Canvas properties for the schema"""
    width: int = 1200
    height: int = 800
    grid_size: int = 20
    theme: str = "default"
    zoom: float = 1.0


@dataclass
class SchemaMetadata:
    """Metadata for the entire schema"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    dracon_version: str = "1.0"


@dataclass
class DraconSchema:
    """Complete DRACON schema representation"""
    metadata: SchemaMetadata
    canvas: CanvasProperties = field(default_factory=CanvasProperties)
    nodes: List[DraconNode] = field(default_factory=list)
    edges: List[DraconEdge] = field(default_factory=list)
    macros: List[MacroDefinition] = field(default_factory=list)
    validation_rules: ValidationRules = field(default_factory=ValidationRules)

    def add_node(self, node: DraconNode) -> None:
        """Add a node to the schema"""
        self.nodes.append(node)

    def add_edge(self, edge: DraconEdge) -> None:
        """Add an edge to the schema"""
        self.edges.append(edge)

    def get_node_by_id(self, node_id: str) -> Optional[DraconNode]:
        """Get a node by its ID"""
        return next((node for node in self.nodes if node.id == node_id), None)

    def get_edges_from_node(self, node_id: str) -> List[DraconEdge]:
        """Get all edges originating from a node"""
        return [edge for edge in self.edges if edge.from_node == node_id]

    def get_edges_to_node(self, node_id: str) -> List[DraconEdge]:
        """Get all edges pointing to a node"""
        return [edge for edge in self.edges if edge.to_node == node_id]


@dataclass
class ParseResult:
    """Result of parsing a DRACON schema"""
    success: bool
    schema: Optional[DraconSchema] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validating a DRACON schema"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    complexity_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderOptions:
    """Options for rendering DRACON schemas"""
    format: str = "svg"  # svg, png, pdf
    theme: str = "default"
    width: int = 1200
    height: int = 800
    show_grid: bool = False
    show_labels: bool = True
    high_contrast: bool = False


@dataclass
class CodeGenerationResult:
    """Result of generating code from DRACON schema"""
    success: bool
    generated_code: str = ""
    files: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# Telegram Bot Integration Types

@dataclass
class BotHandlerInfo:
    """Information about a Telegram bot handler"""
    name: str
    handler_type: str  # command, callback, message
    command_name: Optional[str] = None
    callback_data: Optional[str] = None
    description: str = ""
    dracon_node_id: Optional[str] = None


@dataclass
class BotWorkflowState:
    """State information for bot workflow"""
    user_id: int
    current_node: str
    session_data: Dict[str, Any] = field(default_factory=dict)
    workflow_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)


# File Management Types

class FileCategory(Enum):
    """File categories for DRACON storage"""
    REVERSE = "reverse"
    BUILD = "build"
    AUDIT = "audit"
    LIBRARY = "library"
    ACTIVE = "active"
    ARCHIVE = "archive"
    TEMP = "temp"
    EXPORT = "export"


@dataclass
class DraconFile:
    """File information for DRACON storage"""
    filename: str
    category: FileCategory
    schema: DraconSchema
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    checksum: str = ""


# Constants
DEFAULT_COLORS = {
    "title": "#4a90e2",
    "action": "#7ed321", 
    "question": "#f5a623",
    "case": "#d0021b",
    "loop": "#9013fe",
    "address": "#50e3c2",
    "end": "#b8e986"
}

DRACON_ICONS = {
    NodeType.TITLE: "title_icon.svg",
    NodeType.ACTION: "action_icon.svg",
    NodeType.QUESTION: "question_icon.svg",
    NodeType.CASE: "case_icon.svg",
    NodeType.LOOP_START: "loop_start_icon.svg",
    NodeType.LOOP_END: "loop_end_icon.svg",
    NodeType.ADDRESS: "address_icon.svg",
    NodeType.END: "end_icon.svg"
}

# Validation constants
MAX_NODES_PER_SCHEMA = 1000
MAX_EDGES_PER_SCHEMA = 2000
MAX_MACRO_DEPTH = 10
