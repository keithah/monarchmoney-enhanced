"""
GraphQL Schema Monitoring and Validation for MonarchMoney Enhanced.

This module provides comprehensive schema monitoring, change detection,
and validation capabilities to ensure the library stays compatible with
Monarch Money's evolving GraphQL API.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

from gql import gql
from gql.dsl import DSLQuery, DSLSchema, dsl_gql

from .exceptions import SchemaValidationError, MonarchMoneyError
from .logging_config import MonarchLogger


class SchemaMonitor:
    """
    Monitor GraphQL schema changes and validate operations.

    This class provides functionality to:
    - Introspect the current GraphQL schema
    - Compare schemas for changes
    - Validate existing operations against current schema
    - Generate reports on schema evolution
    """

    def __init__(self, client: "MonarchMoney"):
        """
        Initialize schema monitor.

        Args:
            client: Authenticated MonarchMoney client
        """
        self.client = client
        self.logger = MonarchLogger(self.__class__.__name__)

        # Schema cache directory
        self.cache_dir = Path.home() / ".monarchmoney" / "schema_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Current schema cache
        self._current_schema: Optional[Dict[str, Any]] = None
        self._schema_timestamp: Optional[datetime] = None
        self._schema_cache_duration = timedelta(hours=1)  # Cache for 1 hour

    async def introspect_schema(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get current GraphQL schema from Monarch Money API.

        Args:
            force_refresh: Force refresh even if cached schema is recent

        Returns:
            Complete GraphQL schema introspection result

        Raises:
            SchemaValidationError: If introspection fails
        """
        # Return cached schema if recent
        if (not force_refresh and
            self._current_schema and
            self._schema_timestamp and
            datetime.now() - self._schema_timestamp < self._schema_cache_duration):
            self.logger.debug("Using cached schema")
            return self._current_schema

        self.logger.info("Introspecting GraphQL schema")

        introspection_query = gql("""
            query IntrospectionQuery {
                __schema {
                    queryType { name }
                    mutationType { name }
                    subscriptionType { name }
                    types {
                        ...FullType
                    }
                    directives {
                        name
                        description
                        locations
                        args {
                            ...InputValue
                        }
                    }
                }
            }

            fragment FullType on __Type {
                kind
                name
                description
                fields(includeDeprecated: true) {
                    name
                    description
                    args {
                        ...InputValue
                    }
                    type {
                        ...TypeRef
                    }
                    isDeprecated
                    deprecationReason
                }
                inputFields {
                    ...InputValue
                }
                interfaces {
                    ...TypeRef
                }
                enumValues(includeDeprecated: true) {
                    name
                    description
                    isDeprecated
                    deprecationReason
                }
                possibleTypes {
                    ...TypeRef
                }
            }

            fragment InputValue on __InputValue {
                name
                description
                type { ...TypeRef }
                defaultValue
            }

            fragment TypeRef on __Type {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                        ofType {
                                            kind
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """)

        try:
            result = await self.client.gql_call(
                operation="IntrospectionQuery",
                graphql_query=introspection_query,
                variables={}
            )

            # Cache the result
            self._current_schema = result
            self._schema_timestamp = datetime.now()

            # Save to disk cache
            await self._save_schema_cache(result)

            self.logger.info("Schema introspection completed",
                           types_count=len(result.get("__schema", {}).get("types", [])))

            return result

        except Exception as e:
            self.logger.error("Schema introspection failed", error=str(e))
            raise SchemaValidationError(f"Failed to introspect schema: {e}") from e

    async def _save_schema_cache(self, schema: Dict[str, Any]) -> None:
        """Save schema to disk cache with timestamp."""
        cache_file = self.cache_dir / "latest_schema.json"
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "schema": schema
        }

        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            self.logger.debug("Schema cached to disk", cache_file=str(cache_file))
        except Exception as e:
            self.logger.warning("Failed to cache schema to disk", error=str(e))

    async def _load_schema_cache(self) -> Optional[Dict[str, Any]]:
        """Load schema from disk cache if recent."""
        cache_file = self.cache_dir / "latest_schema.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                cache_data = json.load(f)

            timestamp = datetime.fromisoformat(cache_data["timestamp"])
            if datetime.now() - timestamp < self._schema_cache_duration:
                self.logger.debug("Loaded schema from disk cache")
                return cache_data["schema"]
            else:
                self.logger.debug("Disk cache expired")
                return None

        except Exception as e:
            self.logger.warning("Failed to load schema cache", error=str(e))
            return None

    def get_type_by_name(self, schema: Dict[str, Any], type_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific type from the schema by name."""
        types = schema.get("__schema", {}).get("types", [])
        for type_def in types:
            if type_def.get("name") == type_name:
                return type_def
        return None

    def get_fields_for_type(self, schema: Dict[str, Any], type_name: str) -> List[str]:
        """Get list of field names for a specific type."""
        type_def = self.get_type_by_name(schema, type_name)
        if not type_def or not type_def.get("fields"):
            return []

        return [field["name"] for field in type_def["fields"]]

    def validate_field_exists(self, schema: Dict[str, Any], type_name: str, field_name: str) -> bool:
        """Check if a specific field exists on a type."""
        fields = self.get_fields_for_type(schema, type_name)
        return field_name in fields

    def get_deprecated_fields(self, schema: Dict[str, Any], type_name: str) -> List[Dict[str, Any]]:
        """Get list of deprecated fields for a type."""
        type_def = self.get_type_by_name(schema, type_name)
        if not type_def or not type_def.get("fields"):
            return []

        deprecated_fields = []
        for field in type_def["fields"]:
            if field.get("isDeprecated", False):
                deprecated_fields.append({
                    "name": field["name"],
                    "reason": field.get("deprecationReason", "No reason provided")
                })

        return deprecated_fields

    async def diff_schemas(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed diff between two schemas.

        Args:
            old_schema: Previous schema
            new_schema: Current schema

        Returns:
            Detailed diff report
        """
        self.logger.info("Generating schema diff")

        old_types = {t["name"]: t for t in old_schema.get("__schema", {}).get("types", [])}
        new_types = {t["name"]: t for t in new_schema.get("__schema", {}).get("types", [])}

        diff = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "types_added": 0,
                "types_removed": 0,
                "types_modified": 0,
                "fields_added": 0,
                "fields_removed": 0,
                "fields_deprecated": 0
            },
            "changes": {
                "types_added": [],
                "types_removed": [],
                "types_modified": [],
                "fields_added": {},
                "fields_removed": {},
                "fields_deprecated": {}
            }
        }

        # Find added types
        for type_name in new_types:
            if type_name not in old_types:
                diff["changes"]["types_added"].append(type_name)
                diff["summary"]["types_added"] += 1

        # Find removed types
        for type_name in old_types:
            if type_name not in new_types:
                diff["changes"]["types_removed"].append(type_name)
                diff["summary"]["types_removed"] += 1

        # Find modified types and field changes
        for type_name in old_types:
            if type_name in new_types:
                old_type = old_types[type_name]
                new_type = new_types[type_name]

                type_changes = await self._diff_type_fields(old_type, new_type)
                if type_changes:
                    diff["changes"]["types_modified"].append({
                        "type": type_name,
                        "changes": type_changes
                    })
                    diff["summary"]["types_modified"] += 1

                    # Update field counters
                    diff["summary"]["fields_added"] += len(type_changes.get("fields_added", []))
                    diff["summary"]["fields_removed"] += len(type_changes.get("fields_removed", []))
                    diff["summary"]["fields_deprecated"] += len(type_changes.get("fields_deprecated", []))

        self.logger.info("Schema diff completed",
                        types_added=diff["summary"]["types_added"],
                        types_removed=diff["summary"]["types_removed"],
                        types_modified=diff["summary"]["types_modified"])

        return diff

    async def _diff_type_fields(self, old_type: Dict[str, Any], new_type: Dict[str, Any]) -> Dict[str, Any]:
        """Compare fields between two type definitions."""
        old_fields = {f["name"]: f for f in old_type.get("fields", [])}
        new_fields = {f["name"]: f for f in new_type.get("fields", [])}

        changes = {
            "fields_added": [],
            "fields_removed": [],
            "fields_deprecated": [],
            "fields_modified": []
        }

        # Added fields
        for field_name in new_fields:
            if field_name not in old_fields:
                changes["fields_added"].append(field_name)

        # Removed fields
        for field_name in old_fields:
            if field_name not in new_fields:
                changes["fields_removed"].append(field_name)

        # Modified or deprecated fields
        for field_name in old_fields:
            if field_name in new_fields:
                old_field = old_fields[field_name]
                new_field = new_fields[field_name]

                # Check for deprecation
                old_deprecated = old_field.get("isDeprecated", False)
                new_deprecated = new_field.get("isDeprecated", False)

                if not old_deprecated and new_deprecated:
                    changes["fields_deprecated"].append({
                        "name": field_name,
                        "reason": new_field.get("deprecationReason", "No reason provided")
                    })

        # Return changes only if there are any
        return changes if any(changes.values()) else {}

    async def save_schema_history(self, schema: Dict[str, Any]) -> None:
        """Save schema to historical archive."""
        history_dir = self.cache_dir / "history"
        history_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = history_dir / f"schema_{timestamp}.json"

        try:
            with open(history_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "schema": schema
                }, f, indent=2)

            self.logger.debug("Schema saved to history", file=str(history_file))

            # Clean up old history files (keep last 30 days)
            await self._cleanup_old_history()

        except Exception as e:
            self.logger.warning("Failed to save schema history", error=str(e))

    async def _cleanup_old_history(self) -> None:
        """Remove history files older than 30 days."""
        history_dir = self.cache_dir / "history"
        if not history_dir.exists():
            return

        cutoff_date = datetime.now() - timedelta(days=30)

        for file_path in history_dir.glob("schema_*.json"):
            try:
                # Extract timestamp from filename
                timestamp_str = file_path.stem.replace("schema_", "")
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                if file_date < cutoff_date:
                    file_path.unlink()
                    self.logger.debug("Removed old schema history file", file=str(file_path))
            except Exception as e:
                self.logger.warning("Failed to process history file", file=str(file_path), error=str(e))