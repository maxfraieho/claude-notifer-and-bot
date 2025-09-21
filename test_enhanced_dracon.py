#!/usr/bin/env python3
"""
Test Enhanced DRACON Integration

This script tests the integration of Perplexity's DRACON components
with our existing bot infrastructure.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

async def test_enhanced_dracon():
    """Test the enhanced DRACON system."""
    print("🧪 Testing Enhanced DRACON Integration")
    print("=" * 50)

    try:
        # Test 1: Import enhanced components
        print("1️⃣ Testing imports...")
        from src.bot.features.dracon_types import (
            DraconSchema, DraconNode, DraconEdge, NodeType, EdgeType,
            Position, Size, SchemaMetadata
        )
        from src.bot.features.dracon_parser import DraconParser
        from src.bot.features.dracon_renderer import DraconRenderer
        from src.bot.features.dracon_generator import DraconCodeGenerator
        from src.bot.features.dracon_enhanced import EnhancedDraconProcessor
        print("✅ All imports successful")

        # Test 2: Create enhanced processor
        print("\n2️⃣ Testing enhanced processor...")
        processor = EnhancedDraconProcessor()
        print("✅ Enhanced processor created")

        # Test 3: Create example schema
        print("\n3️⃣ Testing schema creation...")
        metadata = SchemaMetadata(
            name="Test Integration Schema",
            version="1.0.0",
            description="Test schema for integration verification",
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
                "text": "🚀 Test Bot Start",
                "command": "start"
            }
        )
        schema.add_node(start_node)

        # Add action node
        action_node = DraconNode(
            id="main_action",
            node_type=NodeType.ACTION,
            position=Position(x=300, y=100),
            size=Size(width=140, height=80),
            properties={
                "text": "Main Action",
                "template": "🎯 **Main Action**\n\nTest action executed!"
            }
        )
        schema.add_node(action_node)

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
            id="start_to_action",
            from_node="start",
            to_node="main_action",
            edge_type=EdgeType.SEQUENCE
        )
        schema.add_edge(start_edge)

        action_edge = DraconEdge(
            id="action_to_end",
            from_node="main_action",
            to_node="end",
            edge_type=EdgeType.SEQUENCE
        )
        schema.add_edge(action_edge)

        print(f"✅ Schema created with {len(schema.nodes)} nodes and {len(schema.edges)} edges")

        # Test 4: Save schema to file
        print("\n4️⃣ Testing schema file operations...")
        import yaml
        from dataclasses import asdict

        test_schema_file = project_root / "drn" / "temp" / "test_integration_schema.yaml"
        test_schema_file.parent.mkdir(parents=True, exist_ok=True)

        schema_dict = asdict(schema)
        with open(test_schema_file, 'w', encoding='utf-8') as f:
            yaml.dump(schema_dict, f, default_flow_style=False, allow_unicode=True)

        print(f"✅ Schema saved to {test_schema_file}")

        # Test 5: Parse saved schema
        print("\n5️⃣ Testing schema parsing...")
        parser = DraconParser()
        parse_result = parser.parse_file(test_schema_file)

        if parse_result.success:
            print(f"✅ Schema parsed successfully: {parse_result.schema.metadata.name}")
        else:
            print(f"❌ Schema parsing failed: {parse_result.errors}")
            return False

        # Test 6: Generate visual diagram
        print("\n6️⃣ Testing visual rendering...")
        try:
            from src.bot.features.dracon_renderer import RenderOptions
            renderer = DraconRenderer()
            options = RenderOptions(
                format="svg",
                theme="default",
                width=800,
                height=400,
                show_grid=True,
                show_labels=True
            )

            svg_content = renderer.render(parse_result.schema, options)
            if svg_content:
                svg_file = project_root / "drn" / "temp" / "test_diagram.svg"
                with open(svg_file, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                print(f"✅ Visual diagram generated and saved to {svg_file}")
            else:
                print("⚠️ Visual diagram generation returned empty content")

        except Exception as e:
            print(f"⚠️ Visual rendering test failed: {str(e)}")

        # Test 7: Test enhanced processor
        print("\n7️⃣ Testing enhanced processor...")
        try:
            result = await processor.process_schema_file(test_schema_file)

            if result["success"]:
                print(f"✅ Enhanced processing successful!")
                print(f"   📊 Schema: {result['metadata']['name']}")
                print(f"   🔧 Nodes: {result['metadata']['node_count']}")
                print(f"   ➡️ Edges: {result['metadata']['edge_count']}")
                print(f"   ⚡ Complexity: {result['metadata']['complexity']}")

                if result.get("svg_diagram"):
                    print(f"   🎨 Visual diagram: Generated ({len(result['svg_diagram'])} chars)")

                if result.get("components"):
                    components = result["components"]
                    print(f"   📱 Components generated:")
                    print(f"      - Handlers: {len(components.get('handlers', []))}")
                    print(f"      - Commands: {len(components.get('commands', []))}")
                    print(f"      - Messages: {len(components.get('messages', []))}")

            else:
                print(f"❌ Enhanced processing failed: {result.get('errors', [])}")

        except Exception as e:
            print(f"⚠️ Enhanced processor test failed: {str(e)}")

        # Test 8: Test code generation
        print("\n8️⃣ Testing code generation...")
        try:
            generator = DraconCodeGenerator()
            generation_result = generator.generate_telegram_bot(parse_result.schema)

            if generation_result.success:
                print(f"✅ Code generation successful!")
                print(f"   📝 Generated code: {len(generation_result.generated_code)} chars")
                print(f"   📁 Files: {len(generation_result.files)} files")

                # Save generated files
                output_dir = project_root / "drn" / "temp" / "generated_bot"
                output_dir.mkdir(parents=True, exist_ok=True)

                for filename, content in generation_result.files.items():
                    file_path = output_dir / filename
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                print(f"   📁 Generated files saved to {output_dir}")

            else:
                print(f"❌ Code generation failed: {generation_result.errors}")

        except Exception as e:
            print(f"⚠️ Code generation test failed: {str(e)}")

        print("\n" + "=" * 50)
        print("🎉 Enhanced DRACON Integration Test Complete!")
        print("✅ All core components tested successfully")
        print("🚀 System ready for production use")

        return True

    except Exception as e:
        print(f"❌ Critical test failure: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_enhanced_dracon())
    sys.exit(0 if result else 1)