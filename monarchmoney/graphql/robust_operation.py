"""
Robust GraphQL Operations for MonarchMoney Enhanced.

This module provides base classes and utilities for creating GraphQL operations
that are resilient to schema changes, with automatic fallbacks and field validation.
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set, Union
from dataclasses import dataclass, field

from gql import gql
from gql.dsl import DSLQuery, DSLSchema

from ..exceptions import SchemaValidationError
from ..logging_config import MonarchLogger


@dataclass
class FieldSpec:
    """Specification for a GraphQL field with metadata."""
    name: str
    required: bool = False
    deprecated_alternatives: List[str] = field(default_factory=list)
    fallback_value: Any = None
    validation_pattern: Optional[str] = None


@dataclass
class OperationResult:
    """Result of a robust GraphQL operation."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    fields_used: List[str] = field(default_factory=list)
    fields_missing: List[str] = field(default_factory=list)
    fallbacks_used: List[str] = field(default_factory=list)


class RobustGraphQLOperation(ABC):
    """
    Base class for schema-resilient GraphQL operations.

    This class provides functionality to:
    - Validate field availability before execution
    - Automatically fallback to alternative fields
    - Generate queries using only available fields
    - Provide detailed operation results with warnings
    """

    def __init__(self, operation_name: str, operation_type: str = "query"):
        """
        Initialize robust operation.

        Args:
            operation_name: Name of the GraphQL operation
            operation_type: Type of operation (query, mutation, subscription)
        """
        self.operation_name = operation_name
        self.operation_type = operation_type
        self.logger = MonarchLogger(f"{self.__class__.__name__}")

        # Field specifications - to be defined by subclasses
        self.required_fields: List[FieldSpec] = []
        self.optional_fields: List[FieldSpec] = []
        self.response_type: str = ""

        # Runtime state
        self._available_fields: Optional[Set[str]] = None
        self._validated_fields: Optional[List[str]] = None

    @abstractmethod
    def get_base_query_template(self) -> str:
        """
        Get the base GraphQL query template.

        Returns:
            GraphQL query string with field placeholders
        """
        pass

    @abstractmethod
    def process_response(self, raw_response: Dict[str, Any]) -> OperationResult:
        """
        Process the raw GraphQL response into an OperationResult.

        Args:
            raw_response: Raw response from GraphQL API

        Returns:
            Processed operation result
        """
        pass

    def add_required_field(self, name: str, **kwargs) -> None:
        """Add a required field to the operation."""
        self.required_fields.append(FieldSpec(name=name, required=True, **kwargs))

    def add_optional_field(self, name: str, **kwargs) -> None:
        """Add an optional field to the operation."""
        self.optional_fields.append(FieldSpec(name=name, required=False, **kwargs))

    async def validate_against_schema(self, schema_monitor) -> Dict[str, Any]:
        """
        Validate operation fields against current schema.

        Args:
            schema_monitor: SchemaMonitor instance

        Returns:
            Validation results with available/missing fields
        """
        self.logger.debug("Validating operation against schema", operation=self.operation_name)

        schema = await schema_monitor.introspect_schema()

        validation_result = {
            "operation_name": self.operation_name,
            "response_type": self.response_type,
            "required_fields_available": [],
            "required_fields_missing": [],
            "optional_fields_available": [],
            "optional_fields_missing": [],
            "deprecated_fields": [],
            "alternative_fields": {}
        }

        # Check required fields
        for field_spec in self.required_fields:
            if schema_monitor.validate_field_exists(schema, self.response_type, field_spec.name):
                validation_result["required_fields_available"].append(field_spec.name)
            else:
                validation_result["required_fields_missing"].append(field_spec.name)

                # Check for alternatives
                alternatives = self._find_field_alternatives(schema_monitor, schema, field_spec)
                if alternatives:
                    validation_result["alternative_fields"][field_spec.name] = alternatives

        # Check optional fields
        for field_spec in self.optional_fields:
            if schema_monitor.validate_field_exists(schema, self.response_type, field_spec.name):
                validation_result["optional_fields_available"].append(field_spec.name)
            else:
                validation_result["optional_fields_missing"].append(field_spec.name)

        # Check for deprecated fields
        deprecated_fields = schema_monitor.get_deprecated_fields(schema, self.response_type)
        for deprecated_field in deprecated_fields:
            field_name = deprecated_field["name"]
            all_field_names = [f.name for f in self.required_fields + self.optional_fields]
            if field_name in all_field_names:
                validation_result["deprecated_fields"].append(deprecated_field)

        # Cache available fields
        self._available_fields = set(
            validation_result["required_fields_available"] +
            validation_result["optional_fields_available"]
        )

        self.logger.info("Schema validation completed",
                        operation=self.operation_name,
                        required_available=len(validation_result["required_fields_available"]),
                        required_missing=len(validation_result["required_fields_missing"]),
                        optional_available=len(validation_result["optional_fields_available"]),
                        deprecated=len(validation_result["deprecated_fields"]))

        return validation_result

    def _find_field_alternatives(self, schema_monitor, schema: Dict[str, Any], field_spec: FieldSpec) -> List[str]:
        """Find alternative fields for a missing field."""
        alternatives = []

        # Check explicitly defined alternatives
        for alt_name in field_spec.deprecated_alternatives:
            if schema_monitor.validate_field_exists(schema, self.response_type, alt_name):
                alternatives.append(alt_name)

        # Use pattern matching for similar field names
        if field_spec.validation_pattern:
            available_fields = schema_monitor.get_fields_for_type(schema, self.response_type)
            pattern = re.compile(field_spec.validation_pattern, re.IGNORECASE)
            for field_name in available_fields:
                if pattern.match(field_name) and field_name != field_spec.name:
                    alternatives.append(field_name)

        return alternatives

    def build_optimized_query(self, variables: Dict[str, Any]) -> str:
        """
        Build GraphQL query using only available fields.

        Args:
            variables: Variables for the GraphQL operation

        Returns:
            Optimized GraphQL query string

        Raises:
            SchemaValidationError: If required fields are missing
        """
        if self._available_fields is None:
            raise SchemaValidationError("Must validate against schema before building query")

        # Check that all required fields are available
        missing_required = []
        for field_spec in self.required_fields:
            if field_spec.name not in self._available_fields:
                # Check for alternatives
                alternatives_found = []
                for alt_name in field_spec.deprecated_alternatives:
                    if alt_name in self._available_fields:
                        alternatives_found.append(alt_name)

                if not alternatives_found:
                    missing_required.append(field_spec.name)

        if missing_required:
            raise SchemaValidationError(
                f"Required fields missing from schema: {missing_required}"
            )

        # Build field list with available fields
        fields_to_include = []

        # Add required fields (or their alternatives)
        for field_spec in self.required_fields:
            if field_spec.name in self._available_fields:
                fields_to_include.append(field_spec.name)
            else:
                # Use first available alternative
                for alt_name in field_spec.deprecated_alternatives:
                    if alt_name in self._available_fields:
                        fields_to_include.append(alt_name)
                        break

        # Add available optional fields
        for field_spec in self.optional_fields:
            if field_spec.name in self._available_fields:
                fields_to_include.append(field_spec.name)

        # Generate the query
        query_template = self.get_base_query_template()
        fields_string = self._generate_fields_string(fields_to_include)

        # Replace field placeholder in template
        query = query_template.replace("{fields}", fields_string)

        self._validated_fields = fields_to_include

        self.logger.debug("Built optimized query",
                         operation=self.operation_name,
                         fields_count=len(fields_to_include),
                         fields=fields_to_include)

        return query

    def _generate_fields_string(self, fields: List[str]) -> str:
        """Generate GraphQL fields string from field list."""
        # Add proper indentation and __typename
        fields_with_typename = fields + ["__typename"]
        return "\\n".join(f"                        {field}" for field in fields_with_typename)

    async def execute_with_fallbacks(
        self,
        client,
        variables: Dict[str, Any],
        schema_monitor=None
    ) -> OperationResult:
        """
        Execute operation with automatic fallbacks and error handling.

        Args:
            client: GraphQL client
            variables: Operation variables
            schema_monitor: Optional schema monitor for validation

        Returns:
            Operation result with fallback information
        """
        self.logger.info("Executing robust operation", operation=self.operation_name)

        warnings = []
        fallbacks_used = []

        try:
            # Validate against schema if monitor provided
            if schema_monitor:
                validation_result = await self.validate_against_schema(schema_monitor)

                # Add warnings for missing optional fields
                if validation_result["optional_fields_missing"]:
                    warnings.append(
                        f"Optional fields not available: {validation_result['optional_fields_missing']}"
                    )

                # Add warnings for deprecated fields
                if validation_result["deprecated_fields"]:
                    deprecated_names = [f["name"] for f in validation_result["deprecated_fields"]]
                    warnings.append(f"Using deprecated fields: {deprecated_names}")

                # Build optimized query
                query_string = self.build_optimized_query(variables)
            else:
                # Use base query without optimization
                query_string = self.get_base_query_template()
                # Replace with all fields (risky but fallback)
                all_fields = [f.name for f in self.required_fields + self.optional_fields]
                fields_string = self._generate_fields_string(all_fields)
                query_string = query_string.replace("{fields}", fields_string)

            # Execute the query
            query = gql(query_string)
            raw_response = await client.gql_call(
                operation=self.operation_name,
                graphql_query=query,
                variables=variables
            )

            # Process response
            result = self.process_response(raw_response)
            result.warnings.extend(warnings)
            result.fallbacks_used = fallbacks_used
            result.fields_used = self._validated_fields or []

            self.logger.info("Robust operation completed successfully",
                           operation=self.operation_name,
                           warnings_count=len(result.warnings))

            return result

        except Exception as e:
            # Try minimal fallback if primary execution fails
            if "field" in str(e).lower() and schema_monitor:
                self.logger.warning("Primary execution failed, trying minimal fallback",
                                  operation=self.operation_name, error=str(e))

                try:
                    result = await self._execute_minimal_fallback(client, variables)
                    result.warnings.extend(warnings)
                    result.warnings.append(f"Used minimal fallback due to: {str(e)}")
                    result.fallbacks_used.append("minimal_fields")

                    return result
                except Exception as fallback_error:
                    self.logger.error("Minimal fallback also failed",
                                    operation=self.operation_name,
                                    fallback_error=str(fallback_error))

            # Re-raise original error if no fallback worked
            raise

    async def _execute_minimal_fallback(self, client, variables: Dict[str, Any]) -> OperationResult:
        """Execute operation with only the most essential fields."""
        self.logger.debug("Executing minimal fallback", operation=self.operation_name)

        # Use only absolutely required fields
        essential_fields = ["id", "__typename"]
        query_template = self.get_base_query_template()
        fields_string = self._generate_fields_string(essential_fields)
        query_string = query_template.replace("{fields}", fields_string)

        query = gql(query_string)
        raw_response = await client.gql_call(
            operation=self.operation_name,
            graphql_query=query,
            variables=variables
        )

        # Create minimal result
        result = OperationResult(
            success=True,
            data=raw_response,
            fields_used=essential_fields,
            warnings=["Used minimal field set due to schema compatibility issues"]
        )

        return result