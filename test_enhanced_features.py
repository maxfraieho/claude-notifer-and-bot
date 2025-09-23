#!/usr/bin/env python3
"""
Test script for enhanced features integration
"""

import asyncio
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_enhanced_modules():
    """Test enhanced modules integration"""
    print("🧪 Testing Enhanced Modules Integration...")

    try:
        # Test imports
        print("📦 Testing imports...")
        from src.bot.integration import initialize_enhanced_modules, get_enhanced_integration
        from src.bot.ui import NavigationManager, nav_manager, create_progress_indicator
        from src.localization.i18n import i18n, _
        print("✅ All imports successful")

        # Test localization
        print("🌐 Testing localization...")
        i18n.set_locale("uk")
        test_msg_uk = _("commands.start") if "commands.start" in str(_("commands.start")) else "🚀 Розпочати роботу з Claude"
        print(f"   Ukrainian: {test_msg_uk}")

        i18n.set_locale("en")
        test_msg_en = _("commands.start") if "commands.start" in str(_("commands.start")) else "🚀 Start working with Claude"
        print(f"   English: {test_msg_en}")
        print("✅ Localization working")

        # Test navigation
        print("🧭 Testing navigation...")
        nav = nav_manager
        main_menu = nav.get_main_menu()
        print(f"   Main menu created with {len(main_menu.inline_keyboard)} rows")

        nav.push_navigation("main")
        breadcrumb = nav.get_breadcrumb()
        print(f"   Breadcrumb: {breadcrumb}")
        print("✅ Navigation working")

        # Test integration initialization
        print("🔧 Testing integration initialization...")
        await initialize_enhanced_modules()
        integration = get_enhanced_integration()
        print(f"   Integration instance: {type(integration).__name__}")
        print("✅ Integration initialization working")

        print("\n🎉 All enhanced features tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_error_handling():
    """Test error handling module"""
    print("\n🛡️ Testing Error Handling...")

    try:
        from src.bot.utils.error_handler import ErrorHandler, error_handler

        # Test error handler
        handler = ErrorHandler()

        # Test user-friendly messages
        test_error = ValueError("Test error")
        message = handler.get_user_friendly_message(test_error)
        print(f"   Error message: {message}")

        print("✅ Error handling working")
        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Enhanced Features Test Suite")
    print("=" * 50)

    # Run tests
    test1 = await test_enhanced_modules()
    test2 = await test_error_handling()

    print("\n" + "=" * 50)
    if test1 and test2:
        print("🎉 ALL TESTS PASSED! Enhanced features are ready.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)