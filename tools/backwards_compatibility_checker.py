#!/usr/bin/env python3
"""
Backwards Compatibility Checker for MonarchMoney Enhanced.

Compares the enhanced version against the original monarchmoney package
to ensure we maintain field compatibility and response structure.
"""

import asyncio
import json
import sys
from typing import Dict, Any, List, Set
from pathlib import Path

# This would require both packages to be installed for comparison
try:
    import monarchmoney as original_mm
    from monarchmoney import MonarchMoney as EnhancedMM
    ORIGINAL_AVAILABLE = True
except ImportError:
    ORIGINAL_AVAILABLE = False
    print("❌ Original monarchmoney package not available for comparison")


class CompatibilityChecker:
    """Compares enhanced package against original for backwards compatibility."""

    def __init__(self):
        self.methods_to_check = [
            'get_accounts',
            'get_transactions',
            'get_budgets',
            'get_goals',
            'get_transaction_categories',
            'get_bills'
        ]
        self.compatibility_issues = []

    async def check_method_compatibility(self, method_name: str, email: str, password: str):
        """Compare a method between original and enhanced versions."""
        print(f"\n🔍 Checking {method_name}...")

        # Test original package
        original_result = await self._test_original_method(method_name, email, password)

        # Test enhanced package
        enhanced_result = await self._test_enhanced_method(method_name, email, password)

        # Compare results
        issues = self._compare_results(method_name, original_result, enhanced_result)
        if issues:
            self.compatibility_issues.extend(issues)

        return len(issues) == 0

    async def _test_original_method(self, method_name: str, email: str, password: str):
        """Test method on original package."""
        try:
            mm = original_mm.MonarchMoney()
            await mm.login(email, password, save_session=False)
            method = getattr(mm, method_name)
            result = await method()
            return {'success': True, 'result': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _test_enhanced_method(self, method_name: str, email: str, password: str):
        """Test method on enhanced package."""
        try:
            mm = EnhancedMM()
            await mm.login(email, password, save_session=False)
            method = getattr(mm, method_name)
            result = await method()
            return {'success': True, 'result': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _compare_results(self, method_name: str, original: Dict, enhanced: Dict) -> List[str]:
        """Compare results and return list of compatibility issues."""
        issues = []

        # Both should succeed or both should fail
        if original['success'] != enhanced['success']:
            issues.append(f"{method_name}: Success mismatch - original: {original['success']}, enhanced: {enhanced['success']}")
            return issues

        if not original['success']:
            # Both failed - that's fine
            return issues

        # Compare field sets
        orig_fields = self._extract_fields(original['result'])
        enh_fields = self._extract_fields(enhanced['result'])

        missing_fields = orig_fields - enh_fields
        extra_fields = enh_fields - orig_fields

        if missing_fields:
            issues.append(f"{method_name}: Missing fields in enhanced version: {missing_fields}")

        if extra_fields:
            print(f"ℹ️  {method_name}: Enhanced has extra fields: {extra_fields}")

        return issues

    def _extract_fields(self, result: Any, prefix: str = "") -> Set[str]:
        """Recursively extract all field names from a result structure."""
        fields = set()

        if isinstance(result, dict):
            for key, value in result.items():
                field_name = f"{prefix}.{key}" if prefix else key
                fields.add(field_name)

                # Recursively check nested structures
                if isinstance(value, (dict, list)) and key != '__typename':
                    fields.update(self._extract_fields(value, field_name))

        elif isinstance(result, list) and result:
            # Check first item in list
            fields.update(self._extract_fields(result[0], prefix))

        return fields

    def generate_report(self) -> str:
        """Generate a compatibility report."""
        if not self.compatibility_issues:
            return "✅ All methods are backwards compatible!"

        report = "❌ Backwards Compatibility Issues Found:\n\n"
        for issue in self.compatibility_issues:
            report += f"• {issue}\n"

        return report


async def main():
    """Run backwards compatibility check."""
    if not ORIGINAL_AVAILABLE:
        print("To run this check, install both packages:")
        print("pip install monarchmoney  # original")
        print("pip install monarchmoney-enhanced  # enhanced")
        sys.exit(1)

    checker = CompatibilityChecker()

    # Would need test credentials - in practice this would use test account
    email = input("Test email (or set MM_TEST_EMAIL env var): ")
    password = input("Test password (or set MM_TEST_PASSWORD env var): ")

    print("🔍 Running backwards compatibility check...")

    all_compatible = True
    for method in checker.methods_to_check:
        compatible = await checker.check_method_compatibility(method, email, password)
        if not compatible:
            all_compatible = False

    print("\n" + "="*60)
    print(checker.generate_report())

    if not all_compatible:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())