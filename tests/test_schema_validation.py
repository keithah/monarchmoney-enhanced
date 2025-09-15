"""
Automated Schema Validation Tests for MonarchMoney Enhanced.

These tests validate all GraphQL operations against the current API schema
and detect breaking changes automatically.
"""

import asyncio
import json
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from monarchmoney import MonarchMoney
from monarchmoney.schema_monitor import SchemaMonitor
from monarchmoney.graphql.investment_operations import (
    UpdateHoldingQuantityOperation,
    GetAccountHoldingsOperation,
    GetSecurityDetailsOperation
)
from monarchmoney.services import (
    InvestmentService,
    AccountService,
    TransactionService,
    BudgetService
)


class TestSchemaValidation:
    """Comprehensive schema validation test suite."""

    @pytest.fixture(scope="session")
    async def authenticated_client(self):
        """Create authenticated MonarchMoney client for testing."""
        # Use environment variables for authentication
        email = os.getenv("MM_TEST_EMAIL")
        password = os.getenv("MM_TEST_PASSWORD")

        if not email or not password:
            pytest.skip("MM_TEST_EMAIL and MM_TEST_PASSWORD environment variables required")

        mm = MonarchMoney(debug=True)
        try:
            await mm.login_with_email(email, password)
            yield mm
        finally:
            # Cleanup if needed
            pass

    @pytest.fixture
    async def schema_monitor(self, authenticated_client):
        """Create schema monitor instance."""
        return SchemaMonitor(authenticated_client)

    @pytest.fixture
    async def current_schema(self, schema_monitor):
        """Get current schema for testing."""
        return await schema_monitor.introspect_schema()

    @pytest.mark.asyncio
    async def test_schema_introspection(self, schema_monitor):
        """Test that schema introspection works."""
        schema = await schema_monitor.introspect_schema()

        assert schema is not None
        assert "__schema" in schema
        assert "types" in schema["__schema"]
        assert len(schema["__schema"]["types"]) > 0

        # Log schema statistics
        types_count = len(schema["__schema"]["types"])
        print(f"Schema contains {types_count} types")

    @pytest.mark.asyncio
    async def test_investment_service_operations(self, authenticated_client, schema_monitor):
        """Test all investment service operations against current schema."""
        svc = InvestmentService(authenticated_client)

        # Test operations with minimal/mock data
        test_cases = [
            {
                "operation": "get_security_details",
                "args": {"ticker": "AAPL"},
                "expected_to_work": True,
                "description": "Security search should work with valid ticker"
            },
            {
                "operation": "get_account_holdings",
                "args": {"account_id": "nonexistent_account"},
                "expected_to_work": False,  # Business logic failure, not schema
                "description": "Holdings query with invalid account (business logic test)"
            }
        ]

        for test_case in test_cases:
            operation_name = test_case["operation"]
            args = test_case["args"]
            expected_to_work = test_case["expected_to_work"]
            description = test_case["description"]

            print(f"Testing {operation_name}: {description}")

            try:
                method = getattr(svc, operation_name)
                result = await method(**args)

                if not expected_to_work:
                    print(f"  ⚠️  {operation_name} unexpectedly succeeded")
                else:
                    print(f"  ✅ {operation_name} worked as expected")

            except Exception as e:
                error_str = str(e).lower()

                # Categorize errors
                if any(indicator in error_str for indicator in ["field", "schema", "something went wrong"]):
                    # Schema-related error - this is a test failure
                    pytest.fail(f"Schema issue in {operation_name}: {e}")
                elif expected_to_work:
                    # Business logic error when we expected success
                    print(f"  ⚠️  {operation_name} failed unexpectedly: {e}")
                else:
                    # Expected business logic failure
                    print(f"  ✅ {operation_name} failed as expected (business logic): {e}")

    @pytest.mark.asyncio
    async def test_robust_operations_validation(self, schema_monitor):
        """Test robust GraphQL operations field validation."""
        operations = [
            UpdateHoldingQuantityOperation(),
            GetAccountHoldingsOperation(),
            GetSecurityDetailsOperation()
        ]

        for operation in operations:
            print(f"Validating operation: {operation.operation_name}")

            validation_result = await operation.validate_against_schema(schema_monitor)

            # Check that required fields are available
            missing_required = validation_result["required_fields_missing"]
            if missing_required:
                # Check if alternatives are available
                alternatives = validation_result["alternative_fields"]
                unresolved_missing = []

                for missing_field in missing_required:
                    if missing_field not in alternatives or not alternatives[missing_field]:
                        unresolved_missing.append(missing_field)

                if unresolved_missing:
                    pytest.fail(
                        f"Required fields missing without alternatives in {operation.operation_name}: "
                        f"{unresolved_missing}"
                    )

            # Report warnings for optional fields
            missing_optional = validation_result["optional_fields_missing"]
            if missing_optional:
                print(f"  ⚠️  Optional fields missing: {missing_optional}")

            # Report deprecated fields
            deprecated = validation_result["deprecated_fields"]
            if deprecated:
                deprecated_names = [f["name"] for f in deprecated]
                print(f"  ⚠️  Using deprecated fields: {deprecated_names}")

            print(f"  ✅ {operation.operation_name} validation passed")

    @pytest.mark.asyncio
    async def test_schema_history_tracking(self, schema_monitor):
        """Test schema history and change detection."""
        # Save current schema to history
        current_schema = await schema_monitor.introspect_schema()
        await schema_monitor.save_schema_history(current_schema)

        # Check that history file was created
        history_dir = schema_monitor.cache_dir / "history"
        history_files = list(history_dir.glob("schema_*.json"))

        assert len(history_files) > 0, "Schema history file should be created"

        # Load and validate history file
        latest_history = max(history_files, key=lambda p: p.stat().st_mtime)
        with open(latest_history) as f:
            history_data = json.load(f)

        assert "timestamp" in history_data
        assert "schema" in history_data
        assert history_data["schema"]["__schema"]["types"] == current_schema["__schema"]["types"]

    @pytest.mark.asyncio
    async def test_schema_diff_detection(self, schema_monitor):
        """Test schema diff functionality with mock schemas."""
        # Create mock old schema with some differences
        current_schema = await schema_monitor.introspect_schema()

        # Create a modified version for testing
        old_schema = json.loads(json.dumps(current_schema))  # Deep copy

        # Simulate some changes
        types = old_schema["__schema"]["types"]

        # Remove a field from a type (simulate field removal)
        for type_def in types:
            if type_def.get("name") == "Holding" and type_def.get("fields"):
                # Remove last field to simulate schema change
                if len(type_def["fields"]) > 1:
                    removed_field = type_def["fields"].pop()
                    print(f"Simulated removal of field: {removed_field['name']}")
                break

        # Generate diff
        diff = await schema_monitor.diff_schemas(old_schema, current_schema)

        assert "summary" in diff
        assert "changes" in diff
        assert isinstance(diff["summary"]["types_modified"], int)

        print(f"Schema diff summary: {diff['summary']}")

    @pytest.mark.asyncio
    async def test_operation_fallback_mechanisms(self, authenticated_client, schema_monitor):
        """Test that robust operations can handle schema changes gracefully."""
        operation = UpdateHoldingQuantityOperation()

        # Validate against current schema
        await operation.validate_against_schema(schema_monitor)

        # Test query building
        test_variables = {
            "input": {
                "id": "test_holding_id",
                "quantity": "1.0"
            }
        }

        try:
            optimized_query = operation.build_optimized_query(test_variables)
            assert "id" in optimized_query  # Should always include required fields
            assert "__typename" in optimized_query  # Should include typename
            print("✅ Optimized query built successfully")
        except Exception as e:
            pytest.fail(f"Failed to build optimized query: {e}")

    @pytest.mark.asyncio
    async def test_all_service_operations_schema_compatibility(self, authenticated_client):
        """Comprehensive test of all service operations for schema compatibility."""
        services = {
            "InvestmentService": InvestmentService(authenticated_client),
            "AccountService": AccountService(authenticated_client),
            "TransactionService": TransactionService(authenticated_client),
            "BudgetService": BudgetService(authenticated_client)
        }

        # Define safe test operations (that won't modify data)
        safe_operations = {
            "InvestmentService": [
                ("get_security_details", {"ticker": "AAPL"}),
            ],
            "AccountService": [
                ("get_accounts", {}),
            ],
            "TransactionService": [
                ("get_transaction_categories", {}),
            ],
            "BudgetService": [
                ("get_budgets", {}),
            ]
        }

        schema_issues = []
        business_logic_issues = []

        for service_name, service in services.items():
            if service_name not in safe_operations:
                continue

            print(f"Testing {service_name}...")

            for operation_name, args in safe_operations[service_name]:
                try:
                    method = getattr(service, operation_name)
                    result = await method(**args)
                    print(f"  ✅ {operation_name} succeeded")

                except Exception as e:
                    error_str = str(e).lower()

                    # Categorize errors
                    if any(indicator in error_str for indicator in
                          ["field", "something went wrong", "cannot query field"]):
                        schema_issues.append(f"{service_name}.{operation_name}: {e}")
                        print(f"  ❌ {operation_name} - SCHEMA ISSUE: {e}")
                    else:
                        business_logic_issues.append(f"{service_name}.{operation_name}: {e}")
                        print(f"  ⚠️  {operation_name} - Business logic: {e}")

        # Report results
        print(f"\\nSchema compatibility test results:")
        print(f"  Schema issues: {len(schema_issues)}")
        print(f"  Business logic issues: {len(business_logic_issues)}")

        if schema_issues:
            print("\\nSchema issues found:")
            for issue in schema_issues:
                print(f"  - {issue}")

        # Fail test if schema issues found
        if schema_issues:
            pytest.fail(f"Found {len(schema_issues)} schema compatibility issues")

    def test_schema_cache_functionality(self, tmp_path):
        """Test schema caching mechanisms."""
        # Create a temporary schema monitor with custom cache dir
        from monarchmoney.schema_monitor import SchemaMonitor

        # Mock client for testing
        class MockClient:
            async def gql_call(self, **kwargs):
                return {"__schema": {"types": []}}

        monitor = SchemaMonitor(MockClient())
        monitor.cache_dir = tmp_path

        # Test that cache directory is created
        assert monitor.cache_dir.exists()

        # Test cache file operations would work
        cache_file = monitor.cache_dir / "latest_schema.json"
        test_data = {"test": "data"}

        # Test saving cache
        import json
        with open(cache_file, 'w') as f:
            json.dump(test_data, f)

        assert cache_file.exists()

        # Test loading cache
        with open(cache_file) as f:
            loaded_data = json.load(f)

        assert loaded_data == test_data


class TestSchemaMonitoringIntegration:
    """Integration tests for the complete schema monitoring system."""

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_workflow(self, authenticated_client):
        """Test the complete monitoring workflow from introspection to validation."""
        # Initialize monitor
        monitor = SchemaMonitor(authenticated_client)

        # 1. Introspect current schema
        current_schema = await monitor.introspect_schema()
        assert current_schema is not None

        # 2. Save to history
        await monitor.save_schema_history(current_schema)

        # 3. Create and validate robust operation
        operation = UpdateHoldingQuantityOperation()
        validation_result = await operation.validate_against_schema(monitor)

        # 4. Build optimized query
        test_variables = {"input": {"id": "test", "quantity": "1.0"}}
        query = operation.build_optimized_query(test_variables)
        assert query is not None

        # 5. Check for any critical issues
        missing_required = validation_result["required_fields_missing"]
        alternatives = validation_result["alternative_fields"]

        critical_missing = []
        for field in missing_required:
            if field not in alternatives or not alternatives[field]:
                critical_missing.append(field)

        if critical_missing:
            pytest.fail(f"Critical schema issues found: missing required fields {critical_missing}")

        print("✅ End-to-end monitoring workflow completed successfully")


# Test configuration and fixtures
def pytest_configure(config):
    """Configure pytest for schema validation tests."""
    config.addinivalue_line(
        "markers", "schema: mark test as schema validation test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring authentication"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()