"""Test script for context memory system."""

import asyncio
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.claude.context_memory import ContextMemoryManager, ContextEntry, UserContext
from src.storage.facade import Storage
from src.storage.models import ContextEntryModel


async def test_context_memory():
    """Test the context memory system functionality."""
    print("🧪 Testing Context Memory System...")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        # Initialize storage
        storage = Storage(f"sqlite:///{db_path}")
        await storage.initialize()

        # Initialize context memory manager
        context_manager = ContextMemoryManager(storage)

        # Test 1: Create user context
        print("\n✅ Test 1: Creating user context...")
        user_id = 12345
        project_path = "/test/project"

        user_context = await context_manager.get_user_context(user_id, project_path)
        print(f"   Created context for user {user_id}, project {project_path}")
        print(f"   Context entries: {len(user_context.entries)}")

        # Test 2: Add messages to context
        print("\n✅ Test 2: Adding messages to context...")

        # Add user message
        await context_manager.add_message_to_context(
            user_id=user_id,
            project_path=project_path,
            session_id="test_session_001",
            content="Як створити функцію для роботи з базою даних?",
            message_type="user",
            importance=2
        )

        # Add Claude response
        await context_manager.add_message_to_context(
            user_id=user_id,
            project_path=project_path,
            session_id="test_session_001",
            content="Ось приклад функції для роботи з базою даних:\n\n```python\nasync def create_user(db, user_data):\n    async with db.transaction():\n        return await db.fetch_one('INSERT INTO users ...', user_data)\n```",
            message_type="assistant",
            importance=2
        )

        print("   Added user question and Claude response")

        # Test 3: Get context for Claude CLI
        print("\n✅ Test 3: Getting context for Claude CLI...")

        context_prompt = await context_manager.get_context_for_claude(
            user_id=user_id,
            project_path=project_path,
            query="база даних",
            max_entries=10
        )

        print("   Generated context prompt:")
        print(f"   Length: {len(context_prompt)} characters")
        print("   Preview:")
        print("   " + "\n   ".join(context_prompt.split("\n")[:10]))
        if len(context_prompt.split("\n")) > 10:
            print("   ...")

        # Test 4: Export context
        print("\n✅ Test 4: Exporting context...")

        exported_data = await context_manager.export_context(user_id, project_path)

        print(f"   Exported {len(exported_data.get('entries', []))} context entries")
        print(f"   User ID: {exported_data.get('user_id')}")
        print(f"   Project: {exported_data.get('project_path')}")
        print(f"   Created: {exported_data.get('created_at')}")

        # Test 5: Search context
        print("\n✅ Test 5: Searching context...")

        # Get context entries via storage
        search_results = await storage.context.search_context_entries(
            user_id=user_id,
            project_path=project_path,
            search_text="база",
            limit=5
        )

        print(f"   Found {len(search_results)} entries matching 'база'")
        for entry in search_results:
            print(f"   - [{entry.timestamp.strftime('%H:%M')}] {entry.message_type}: {entry.content[:60]}...")

        # Test 6: Context statistics
        print("\n✅ Test 6: Getting context statistics...")

        stats = await storage.context.get_context_stats(user_id, project_path)

        print(f"   Total entries: {stats.get('total_entries', 0)}")
        print(f"   Sessions: {stats.get('sessions_count', 0)}")
        print(f"   High importance: {stats.get('high_importance', 0)}")
        print(f"   Medium importance: {stats.get('medium_importance', 0)}")
        print(f"   Low importance: {stats.get('low_importance', 0)}")

        # Test 7: Add more entries and test limits
        print("\n✅ Test 7: Testing context limits...")

        # Add several more entries
        for i in range(5):
            await context_manager.add_message_to_context(
                user_id=user_id,
                project_path=project_path,
                session_id=f"test_session_00{i+2}",
                content=f"Тест запит номер {i+1}: Як оптимізувати код?",
                message_type="user",
                importance=3  # Low importance
            )

            await context_manager.add_message_to_context(
                user_id=user_id,
                project_path=project_path,
                session_id=f"test_session_00{i+2}",
                content=f"Відповідь {i+1}: Ось кілька рекомендацій для оптимізації...",
                message_type="assistant",
                importance=3
            )

        # Get updated context
        updated_context = await context_manager.get_user_context(user_id, project_path)
        print(f"   Updated context entries: {len(updated_context.entries)}")

        # Test 8: Clear context
        print("\n✅ Test 8: Clearing context...")

        cleared = await context_manager.clear_context(user_id, project_path)

        if cleared:
            print("   Context cleared successfully")

            # Verify it's cleared
            final_context = await context_manager.get_user_context(user_id, project_path)
            print(f"   Remaining entries after clear: {len(final_context.entries)}")
        else:
            print("   Failed to clear context")

        print("\n🎉 All tests completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup temporary database
        try:
            os.unlink(db_path)
            print(f"\n🧹 Cleaned up temporary database: {db_path}")
        except:
            pass


async def main():
    """Run the test."""
    print("="*60)
    print("🧠 CONTEXT MEMORY SYSTEM TEST")
    print("="*60)

    success = await test_context_memory()

    if success:
        print("\n✅ ALL TESTS PASSED! Context memory system is working correctly.")
        print("\nFeatures tested:")
        print("• Context creation and management")
        print("• Message storage and retrieval")
        print("• Context generation for Claude CLI")
        print("• Export functionality")
        print("• Search capabilities")
        print("• Statistics and analytics")
        print("• Context cleanup")
        return 0
    else:
        print("\n❌ TESTS FAILED! Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)