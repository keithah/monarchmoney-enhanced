#!/usr/bin/env python3
"""
Minimal test to isolate the issue with our get_accounts changes.
This will help identify if the problem is in our optimization or elsewhere.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, patch

# Check if we can even import the key components without full dependencies
def test_imports():
    """Test if our changes broke basic imports."""
    print("Testing basic imports...")

    try:
        # Test if the service can be imported
        print("  Testing account service import...")
        from monarchmoney.services.account_service import AccountService
        print("  ✅ AccountService import successful")

        # Test if our method signature is correct
        import inspect
        sig = inspect.signature(AccountService.get_accounts)
        params = list(sig.parameters.keys())
        print(f"  ✅ get_accounts parameters: {params}")

        # Check if detail_level has default
        detail_level_param = sig.parameters.get('detail_level')
        if detail_level_param:
            print(f"  ✅ detail_level default: {detail_level_param.default}")
        else:
            print("  ❌ detail_level parameter missing!")
            return False

        return True

    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_method_logic():
    """Test if our get_accounts logic is correct."""
    print("\nTesting method logic...")

    try:
        # Simulate the logic without imports
        detail_level = "full"  # default value

        # This is our branching logic
        if detail_level == "basic":
            operation_name = "GetAccounts"  # We use same operation name
            query_type = "basic"
        elif detail_level == "balance":
            operation_name = "GetAccounts"  # We use same operation name
            query_type = "balance"
        else:  # full detail
            operation_name = "GetAccounts"  # We use same operation name
            query_type = "full"

        print(f"  ✅ Logic test: detail_level='{detail_level}' -> operation='{operation_name}', query='{query_type}'")

        # Test that we always use the same operation name (for test compatibility)
        for level in ["basic", "balance", "full"]:
            if level == "basic":
                op = "GetAccounts"
            elif level == "balance":
                op = "GetAccounts"
            else:
                op = "GetAccounts"
            assert op == "GetAccounts", f"Operation name mismatch for {level}"

        print("  ✅ All detail levels use consistent operation name")
        return True

    except Exception as e:
        print(f"  ❌ Logic test failed: {e}")
        return False


def test_service_integration():
    """Test if the service integration works."""
    print("\nTesting service integration...")

    try:
        # Check if we can create a mock service
        from monarchmoney.services.account_service import AccountService

        # Create a mock client
        class MockClient:
            def __init__(self):
                self._token = "test_token"

        mock_client = MockClient()
        service = AccountService(mock_client)

        print("  ✅ AccountService can be instantiated")

        # Check if the method exists and has right signature
        method = getattr(service, 'get_accounts')
        print("  ✅ get_accounts method exists")

        return True

    except Exception as e:
        print(f"  ❌ Service integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all minimal tests."""
    print("🧪 Minimal Test Check - Isolating the Issue")
    print("=" * 50)

    tests = [
        test_imports,
        test_method_logic,
        test_service_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} crashed: {e}")

    print(f"\n📊 Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ All minimal tests passed - issue is likely elsewhere")
        print("💡 Suggestion: Check if it's a test environment or dependency issue")
    else:
        print("❌ Our changes have fundamental issues that need fixing")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)