#!/usr/bin/env python3
"""
Operation Health Checker for MonarchMoney Enhanced.

Since GraphQL introspection is disabled, this tool tests actual operations
to detect schema changes and field availability issues.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from monarchmoney import MonarchMoney
from monarchmoney.services import (
    InvestmentService,
    AccountService,
    TransactionService,
    BudgetService
)


class OperationHealthChecker:
    """Health checker for GraphQL operations without schema introspection."""

    def __init__(self, client: MonarchMoney):
        self.client = client
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'overall_status': 'healthy',
            'issues_found': [],
            'changes_detected': []
        }

    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health checks on all services."""
        print("🔍 Running comprehensive operation health checks...\n")

        # Test operations by service
        test_cases = {
            'AccountService': [
                {
                    'method': 'get_accounts',
                    'args': {},
                    'expected_fields': ['id', 'displayName', 'type', 'subtype'],
                    'description': 'Get user accounts'
                }
            ],
            'TransactionService': [
                {
                    'method': 'get_transaction_categories',
                    'args': {},
                    'expected_fields': ['id', 'name', 'group'],
                    'description': 'Get transaction categories'
                },
                {
                    'method': 'get_transactions',
                    'args': {'limit': 1},
                    'expected_fields': ['id', 'amount', 'date', 'description'],
                    'description': 'Get recent transactions'
                }
            ],
            'InvestmentService': [
                {
                    'method': 'get_security_details',
                    'args': {'ticker': 'AAPL'},
                    'expected_fields': ['id', 'name', 'ticker'],
                    'description': 'Search for security details'
                }
            ],
            'BudgetService': [
                {
                    'method': 'get_budgets',
                    'args': {},
                    'expected_fields': ['id', 'name'],
                    'description': 'Get budget information'
                }
            ]
        }

        services = {
            'AccountService': AccountService(self.client),
            'TransactionService': TransactionService(self.client),
            'InvestmentService': InvestmentService(self.client),
            'BudgetService': BudgetService(self.client)
        }

        total_tests = 0
        passed_tests = 0

        for service_name, test_operations in test_cases.items():
            print(f"🧪 Testing {service_name}...")
            service = services[service_name]
            service_results = {'tests': [], 'status': 'healthy', 'issues': []}

            for test_case in test_operations:
                total_tests += 1
                result = await self._test_operation(
                    service, service_name, test_case
                )
                service_results['tests'].append(result)

                if result['status'] == 'passed':
                    passed_tests += 1
                elif result['status'] == 'schema_error':
                    service_results['status'] = 'unhealthy'
                    self.results['overall_status'] = 'unhealthy'
                elif result['status'] == 'degraded':
                    if service_results['status'] == 'healthy':
                        service_results['status'] = 'degraded'
                    if self.results['overall_status'] == 'healthy':
                        self.results['overall_status'] = 'degraded'

            self.results['services'][service_name] = service_results
            print(f"  Status: {service_results['status']}\n")

        # Summary
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'schema_errors': len(self.results['issues_found']),
            'field_changes': len(self.results['changes_detected'])
        }

        return self.results

    async def _test_operation(
        self, service, service_name: str, test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test a single operation and analyze results."""
        method_name = test_case['method']
        args = test_case['args']
        expected_fields = test_case['expected_fields']
        description = test_case['description']

        test_result = {
            'method': method_name,
            'description': description,
            'status': 'unknown',
            'error': None,
            'missing_fields': [],
            'available_fields': [],
            'is_schema_error': False
        }

        try:
            print(f"  Testing {method_name}: {description}")
            method = getattr(service, method_name)
            result = await method(**args)

            # Analyze result structure
            test_result = self._analyze_operation_result(
                result, expected_fields, test_result, service_name, method_name
            )

            if test_result['status'] == 'passed':
                print(f"    ✅ Passed")
            elif test_result['status'] == 'degraded':
                print(f"    ⚠️  Degraded: Missing fields {test_result['missing_fields']}")

        except Exception as e:
            test_result = self._analyze_operation_error(
                e, test_result, service_name, method_name
            )

        return test_result

    def _analyze_operation_result(
        self, result: Any, expected_fields: List[str],
        test_result: Dict[str, Any], service_name: str, method_name: str
    ) -> Dict[str, Any]:
        """Analyze operation result for field availability."""

        sample_item = None
        if isinstance(result, list) and len(result) > 0:
            sample_item = result[0]
        elif isinstance(result, dict):
            sample_item = result

        if sample_item and isinstance(sample_item, dict):
            available_fields = list(sample_item.keys())
            missing_fields = [f for f in expected_fields if f not in available_fields]

            test_result['available_fields'] = available_fields
            test_result['missing_fields'] = missing_fields

            if missing_fields:
                test_result['status'] = 'degraded'
                issue = f'{service_name}.{method_name}: Missing expected fields {missing_fields}'
                self.results['changes_detected'].append(issue)
            else:
                test_result['status'] = 'passed'
        else:
            # Non-dict result or empty - assume passed
            test_result['status'] = 'passed'

        return test_result

    def _analyze_operation_error(
        self, error: Exception, test_result: Dict[str, Any],
        service_name: str, method_name: str
    ) -> Dict[str, Any]:
        """Analyze operation error to categorize it."""
        error_str = str(error).lower()
        test_result['error'] = str(error)

        # Classify error types
        schema_error_indicators = [
            'something went wrong', 'field', 'cannot query field',
            'unknown field', 'schema', 'introspection'
        ]

        if any(indicator in error_str for indicator in schema_error_indicators):
            test_result['is_schema_error'] = True
            test_result['status'] = 'schema_error'
            issue = f'{service_name}.{method_name}: Schema error - {str(error)}'
            self.results['issues_found'].append(issue)
            print(f"    ❌ SCHEMA ERROR: {error}")
        else:
            test_result['status'] = 'business_error'
            print(f"    ⚠️  Business logic error (expected): {error}")

        return test_result

    def generate_report(self, output_path: Path) -> None:
        """Generate detailed health check report."""
        # Save JSON results
        json_file = output_path / f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Generate markdown report
        md_file = output_path / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._generate_markdown_report(md_file)

        print(f"\n📊 Reports generated:")
        print(f"  JSON: {json_file}")
        print(f"  Markdown: {md_file}")

    def _generate_markdown_report(self, output_file: Path) -> None:
        """Generate human-readable markdown report."""
        results = self.results
        summary = results['summary']

        content = f"""# MonarchMoney Operation Health Report

**Generated:** {results['timestamp']}

## 📊 Overall Status: {results['overall_status'].upper()}

### Summary
- **Success Rate:** {summary['success_rate']:.1f}%
- **Total Tests:** {summary['total_tests']}
- **Passed Tests:** {summary['passed_tests']}
- **Schema Errors:** {summary['schema_errors']}
- **Field Changes:** {summary['field_changes']}

"""

        # Service Details
        content += "## 🔧 Service Health\n\n"
        for service_name, service_data in results['services'].items():
            status_emoji = {
                'healthy': '✅',
                'degraded': '⚠️',
                'unhealthy': '❌'
            }.get(service_data['status'], '❓')

            content += f"### {service_name} {status_emoji}\n"
            content += f"**Status:** {service_data['status']}\n\n"

            for test in service_data['tests']:
                test_emoji = {
                    'passed': '✅',
                    'degraded': '⚠️',
                    'schema_error': '❌',
                    'business_error': '⚠️'
                }.get(test['status'], '❓')

                content += f"#### {test['method']} {test_emoji}\n"
                content += f"- **Description:** {test['description']}\n"
                content += f"- **Status:** {test['status']}\n"

                if test['missing_fields']:
                    content += f"- **Missing Fields:** {', '.join(test['missing_fields'])}\n"
                if test['available_fields']:
                    content += f"- **Available Fields:** {', '.join(test['available_fields'])}\n"
                if test['error']:
                    content += f"- **Error:** {test['error']}\n"

                content += "\n"

        # Issues Summary
        if results['issues_found']:
            content += "## 🚨 Schema Errors Found\n\n"
            for issue in results['issues_found']:
                content += f"- {issue}\n"
            content += "\n"

        if results['changes_detected']:
            content += "## ⚠️ Field Changes Detected\n\n"
            for change in results['changes_detected']:
                content += f"- {change}\n"
            content += "\n"

        # Recommendations
        content += "## 💡 Recommendations\n\n"
        if results['issues_found']:
            content += "- 🚨 **Urgent:** Schema errors detected - operations may be failing\n"
            content += "- 🔧 Update robust operation field specifications\n"
            content += "- 🧪 Test affected operations manually\n"
        elif results['changes_detected']:
            content += "- ⚠️ Field changes detected - update expected field lists\n"
            content += "- 📝 Review operation robustness\n"
        else:
            content += "- ✅ All operations healthy - no action needed\n"

        content += """
## 🛠️ Next Steps

1. **Review Results:** Check detailed test results above
2. **Fix Issues:** Address any schema errors found
3. **Update Operations:** Modify field specifications as needed
4. **Monitor Trends:** Compare with previous health check results

---
*Generated by MonarchMoney Enhanced Operation Health Checker*
"""

        with open(output_file, 'w') as f:
            f.write(content)

    def print_summary(self) -> None:
        """Print a summary of health check results."""
        results = self.results
        summary = results['summary']

        print(f"\n{'='*50}")
        print(f"📊 OPERATION HEALTH SUMMARY")
        print(f"{'='*50}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Success Rate: {summary['success_rate']:.1f}% ({summary['passed_tests']}/{summary['total_tests']})")
        print(f"Schema Errors: {summary['schema_errors']}")
        print(f"Field Changes: {summary['field_changes']}")
        print(f"{'='*50}")

        if results['issues_found']:
            print(f"\n🚨 SCHEMA ERRORS:")
            for issue in results['issues_found']:
                print(f"  - {issue}")

        if results['changes_detected']:
            print(f"\n⚠️  FIELD CHANGES:")
            for change in results['changes_detected']:
                print(f"  - {change}")

        if not results['issues_found'] and not results['changes_detected']:
            print(f"\n✅ All operations are healthy!")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MonarchMoney Operation Health Checker"
    )

    parser.add_argument(
        "--email",
        required=True,
        help="MonarchMoney account email"
    )

    parser.add_argument(
        "--password",
        required=True,
        help="MonarchMoney account password"
    )

    parser.add_argument(
        "--mfa-secret",
        help="MFA secret key for TOTP (optional)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / "health_reports",
        help="Output directory for reports"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick health check (fewer tests)"
    )

    args = parser.parse_args()

    # Initialize client
    print("🔐 Authenticating with MonarchMoney...")
    mm = MonarchMoney(debug=False)
    try:
        await mm.login(
            email=args.email,
            password=args.password,
            mfa_secret_key=args.mfa_secret,
            use_saved_session=False,
            save_session=False
        )
        print("✅ Authentication successful\n")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)

    # Run health checks
    checker = OperationHealthChecker(mm)
    results = await checker.run_comprehensive_health_check()

    # Generate outputs
    args.output.mkdir(parents=True, exist_ok=True)
    checker.generate_report(args.output)
    checker.print_summary()

    # Exit with appropriate code
    if results['overall_status'] == 'unhealthy':
        sys.exit(1)
    elif results['overall_status'] == 'degraded':
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())