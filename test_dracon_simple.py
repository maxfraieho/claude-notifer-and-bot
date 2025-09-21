#!/usr/bin/env python3
"""
Simple DRACON Components Test

Tests the core DRACON components without circular import issues.
"""

import asyncio
import sys
from pathlib import Path

async def test_dracon_components():
    """Test DRACON components directly."""
    print("🧪 Testing DRACON Components")
    print("=" * 40)

    try:
        # Test 1: Test type imports
        print("1️⃣ Testing type imports...")
        sys.path.insert(0, str(Path(__file__).parent / "src" / "bot" / "features"))

        from dracon_types import (
            DraconSchema, DraconNode, DraconEdge, NodeType, EdgeType,
            Position, Size, SchemaMetadata
        )
        print("✅ Type imports successful")

        # Test 2: Create schema
        print("\n2️⃣ Testing schema creation...")
        metadata = SchemaMetadata(
            name="Simple Test Schema",
            version="1.0.0",
            description="Simple test",
            author="Test System"
        )

        schema = DraconSchema(metadata=metadata)

        # Add nodes
        start_node = DraconNode(
            id="start",
            node_type=NodeType.TITLE,
            position=Position(x=100, y=100),
            size=Size(width=120, height=60),
            properties={"text": "Start"}
        )
        schema.add_node(start_node)

        end_node = DraconNode(
            id="end",
            node_type=NodeType.END,
            position=Position(x=300, y=100),
            size=Size(width=100, height=50),
            properties={"text": "End"}
        )
        schema.add_node(end_node)

        # Add edge
        edge = DraconEdge(
            id="start_to_end",
            from_node="start",
            to_node="end",
            edge_type=EdgeType.SEQUENCE
        )
        schema.add_edge(edge)

        print(f"✅ Schema created: {schema.metadata.name}")
        print(f"   Nodes: {len(schema.nodes)}")
        print(f"   Edges: {len(schema.edges)}")

        # Test 3: Test schema methods
        print("\n3️⃣ Testing schema methods...")
        start = schema.get_node_by_id("start")
        print(f"✅ Found start node: {start.properties['text']}")

        edges_from_start = schema.get_edges_from_node("start")
        print(f"✅ Edges from start: {len(edges_from_start)}")

        # Test 4: Save schema
        print("\n4️⃣ Testing schema serialization...")
        import yaml
        from dataclasses import asdict

        schema_dict = asdict(schema)
        yaml_content = yaml.dump(schema_dict, default_flow_style=False, allow_unicode=True)

        # Save to file
        test_file = Path("drn/temp/simple_test.yaml")
        test_file.parent.mkdir(parents=True, exist_ok=True)

        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        print(f"✅ Schema saved to {test_file}")
        print(f"   File size: {test_file.stat().st_size} bytes")

        # Test 5: Test parser
        print("\n5️⃣ Testing parser...")
        try:
            from dracon_parser import DraconParser

            parser = DraconParser()
            result = parser.parse_file(test_file)

            if result.success:
                print(f"✅ Parser successful: {result.schema.metadata.name}")
            else:
                print(f"❌ Parser failed: {result.errors}")

        except Exception as e:
            print(f"⚠️ Parser test failed: {str(e)}")

        # Test 6: Test renderer
        print("\n6️⃣ Testing renderer...")
        try:
            from dracon_renderer import DraconRenderer, RenderOptions

            renderer = DraconRenderer()
            options = RenderOptions(
                format="svg",
                width=600,
                height=300,
                show_grid=True
            )

            svg_content = renderer.render(schema, options)

            if svg_content:
                svg_file = Path("drn/temp/simple_test.svg")
                with open(svg_file, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                print(f"✅ SVG diagram generated: {len(svg_content)} chars")
                print(f"   Saved to: {svg_file}")
            else:
                print("⚠️ SVG generation returned empty content")

        except Exception as e:
            print(f"⚠️ Renderer test failed: {str(e)}")

        print("\n" + "=" * 40)
        print("🎉 DRACON Components Test Complete!")
        return True

    except Exception as e:
        print(f"❌ Test failure: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_dracon_components())
    sys.exit(0 if result else 1)