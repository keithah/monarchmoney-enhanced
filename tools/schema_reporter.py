#!/usr/bin/env python3
"""
Schema Monitoring and Reporting Tool for MonarchMoney Enhanced.

This tool provides command-line interface for schema monitoring,
diff generation, and reporting capabilities.
"""

import argparse
import asyncio
import json
import sys
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


class SchemaReporter:
    """Enhanced schema reporting and analysis tool."""

    def __init__(self, client: MonarchMoney):
        self.client = client
        self.monitor = SchemaMonitor(client)

    async def generate_comprehensive_report(self, output_dir: Path) -> Dict[str, Any]:
        """Generate comprehensive schema analysis report."""
        print("Generating comprehensive schema report...")
        output_dir.mkdir(parents=True, exist_ok=True)

        report = {
            "generated_at": datetime.now().isoformat(),
            "schema_analysis": {},
            "operation_compatibility": {},
            "deprecation_warnings": [],
            "breaking_changes": [],
            "recommendations": []
        }

        # 1. Schema introspection and analysis
        print("  📊 Analyzing current schema...")
        current_schema = await self.monitor.introspect_schema()
        report["schema_analysis"] = await self._analyze_schema_structure(current_schema)

        # 2. Operation compatibility analysis
        print("  🔧 Testing operation compatibility...")
        operations = [
            UpdateHoldingQuantityOperation(),
            GetAccountHoldingsOperation(),
            GetSecurityDetailsOperation()
        ]

        for operation in operations:
            compatibility = await self._test_operation_compatibility(operation)
            report["operation_compatibility"][operation.operation_name] = compatibility

        # 3. Historical comparison
        print("  📈 Comparing with historical data...")
        history_analysis = await self._analyze_schema_history()
        if history_analysis:
            report.update(history_analysis)

        # 4. Generate recommendations
        print("  💡 Generating recommendations...")
        report["recommendations"] = self._generate_recommendations(report)

        # Save detailed report
        report_file = output_dir / f"schema_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Generate human-readable summary
        summary_file = output_dir / f"schema_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        await self._generate_markdown_summary(report, summary_file)

        print(f"  ✅ Report saved to {report_file}")
        print(f"  ✅ Summary saved to {summary_file}")

        return report

    async def _analyze_schema_structure(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the structure of the GraphQL schema."""
        types = schema.get("__schema", {}).get("types", [])

        analysis = {
            "total_types": len(types),
            "type_breakdown": {},
            "field_statistics": {},
            "deprecated_items": [],
            "large_types": []  # Types with many fields
        }

        # Analyze type breakdown
        type_kinds = {}
        field_counts = {}
        deprecated_fields = []

        for type_def in types:
            kind = type_def.get("kind", "UNKNOWN")
            type_kinds[kind] = type_kinds.get(kind, 0) + 1

            type_name = type_def.get("name", "Unknown")
            fields = type_def.get("fields", [])

            if fields:
                field_count = len(fields)
                field_counts[type_name] = field_count

                # Check for large types (> 20 fields)
                if field_count > 20:
                    analysis["large_types"].append({
                        "name": type_name,
                        "field_count": field_count
                    })

                # Check for deprecated fields
                for field in fields:
                    if field.get("isDeprecated", False):
                        deprecated_fields.append({
                            "type": type_name,
                            "field": field["name"],
                            "reason": field.get("deprecationReason", "No reason provided")
                        })

        analysis["type_breakdown"] = type_kinds
        analysis["field_statistics"] = {
            "types_with_fields": len(field_counts),
            "average_fields_per_type": sum(field_counts.values()) / len(field_counts) if field_counts else 0,
            "max_fields": max(field_counts.values()) if field_counts else 0,
            "min_fields": min(field_counts.values()) if field_counts else 0
        }
        analysis["deprecated_items"] = deprecated_fields

        return analysis

    async def _test_operation_compatibility(self, operation) -> Dict[str, Any]:
        """Test compatibility of a specific operation."""
        try:
            validation_result = await operation.validate_against_schema(self.monitor)

            compatibility = {
                "status": "compatible",
                "required_fields_status": "ok" if not validation_result["required_fields_missing"] else "issues",
                "optional_fields_available": len(validation_result["optional_fields_available"]),
                "optional_fields_missing": len(validation_result["optional_fields_missing"]),
                "deprecated_fields_in_use": len(validation_result["deprecated_fields"]),
                "issues": [],
                "warnings": []
            }

            # Check for issues
            if validation_result["required_fields_missing"]:
                missing_without_alternatives = []
                for field in validation_result["required_fields_missing"]:
                    alternatives = validation_result["alternative_fields"].get(field, [])
                    if not alternatives:
                        missing_without_alternatives.append(field)

                if missing_without_alternatives:
                    compatibility["status"] = "broken"
                    compatibility["issues"].append(
                        f"Required fields missing without alternatives: {missing_without_alternatives}"
                    )

            # Check for warnings
            if validation_result["optional_fields_missing"]:
                compatibility["warnings"].append(
                    f"Optional fields missing: {validation_result['optional_fields_missing']}"
                )

            if validation_result["deprecated_fields"]:
                deprecated_names = [f["name"] for f in validation_result["deprecated_fields"]]
                compatibility["warnings"].append(
                    f"Using deprecated fields: {deprecated_names}"
                )

            return compatibility

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "issues": [f"Failed to validate operation: {e}"]
            }

    async def _analyze_schema_history(self) -> Optional[Dict[str, Any]]:
        """Analyze schema changes over time."""
        history_dir = self.monitor.cache_dir / "history"
        if not history_dir.exists():
            return None

        history_files = sorted(history_dir.glob("schema_*.json"),
                             key=lambda p: p.stat().st_mtime, reverse=True)

        if len(history_files) < 2:
            return None

        # Compare with most recent previous schema
        current_file = history_files[0]
        previous_file = history_files[1]

        try:
            with open(current_file) as f:
                current_data = json.load(f)
            with open(previous_file) as f:
                previous_data = json.load(f)

            diff = await self.monitor.diff_schemas(
                previous_data["schema"],
                current_data["schema"]
            )

            return {
                "schema_diff": diff,
                "comparison_period": {
                    "from": previous_data["timestamp"],
                    "to": current_data["timestamp"]
                }
            }

        except Exception as e:
            return {
                "history_analysis_error": str(e)
            }

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Check deprecated fields
        operation_compat = report.get("operation_compatibility", {})
        for op_name, compat in operation_compat.items():
            if compat.get("deprecated_fields_in_use", 0) > 0:
                recommendations.append(
                    f"🔄 Update {op_name} to avoid deprecated fields"
                )

            if compat.get("status") == "broken":
                recommendations.append(
                    f"🚨 URGENT: Fix broken operation {op_name}"
                )

        # Check schema diff
        schema_diff = report.get("schema_diff")
        if schema_diff:
            summary = schema_diff.get("summary", {})
            if summary.get("fields_removed", 0) > 0:
                recommendations.append(
                    "⚠️ Fields were removed - review operation queries for compatibility"
                )

            if summary.get("fields_deprecated", 0) > 0:
                recommendations.append(
                    "📝 Plan migration away from newly deprecated fields"
                )

            if summary.get("fields_added", 0) > 0:
                recommendations.append(
                    "✨ Consider using new fields for enhanced functionality"
                )

        # Performance recommendations
        schema_analysis = report.get("schema_analysis", {})
        large_types = schema_analysis.get("large_types", [])
        if large_types:
            recommendations.append(
                f"🎯 Optimize queries for large types: {[t['name'] for t in large_types[:3]]}"
            )

        if not recommendations:
            recommendations.append("✅ No specific recommendations - schema is healthy")

        return recommendations

    async def _generate_markdown_summary(self, report: Dict[str, Any], output_file: Path):
        """Generate human-readable markdown summary."""
        content = f"""# MonarchMoney GraphQL Schema Report

**Generated:** {report['generated_at']}

## 📊 Schema Overview

"""

        # Schema statistics
        schema_analysis = report.get("schema_analysis", {})
        content += f"""### Statistics
- **Total Types:** {schema_analysis.get('total_types', 'Unknown')}
- **Types with Fields:** {schema_analysis.get('field_statistics', {}).get('types_with_fields', 'Unknown')}
- **Average Fields per Type:** {schema_analysis.get('field_statistics', {}).get('average_fields_per_type', 0):.1f}
- **Deprecated Fields:** {len(schema_analysis.get('deprecated_items', []))}

"""

        # Type breakdown
        type_breakdown = schema_analysis.get("type_breakdown", {})
        if type_breakdown:
            content += "### Type Breakdown\\n"
            for kind, count in type_breakdown.items():
                content += f"- **{kind}:** {count}\\n"
            content += "\\n"

        # Operation compatibility
        content += "## 🔧 Operation Compatibility\\n\\n"
        operation_compat = report.get("operation_compatibility", {})

        for op_name, compat in operation_compat.items():
            status = compat.get("status", "unknown")
            status_emoji = {"compatible": "✅", "broken": "❌", "error": "⚠️"}.get(status, "❓")

            content += f"### {op_name} {status_emoji}\\n"
            content += f"- **Status:** {status}\\n"

            if compat.get("issues"):
                content += "- **Issues:**\\n"
                for issue in compat["issues"]:
                    content += f"  - {issue}\\n"

            if compat.get("warnings"):
                content += "- **Warnings:**\\n"
                for warning in compat["warnings"]:
                    content += f"  - {warning}\\n"

            content += "\\n"

        # Schema changes
        schema_diff = report.get("schema_diff")
        if schema_diff:
            content += "## 📈 Recent Changes\\n\\n"
            summary = schema_diff.get("summary", {})

            content += f"""### Change Summary
- **Types Added:** {summary.get('types_added', 0)}
- **Types Removed:** {summary.get('types_removed', 0)}
- **Types Modified:** {summary.get('types_modified', 0)}
- **Fields Added:** {summary.get('fields_added', 0)}
- **Fields Removed:** {summary.get('fields_removed', 0)}
- **Fields Deprecated:** {summary.get('fields_deprecated', 0)}

"""

            # Breaking changes
            if summary.get('types_removed', 0) > 0 or summary.get('fields_removed', 0) > 0:
                content += "### ⚠️ Potential Breaking Changes\\n"
                content += "- Schema changes detected that may break existing operations\\n"
                content += "- Review operation compatibility above\\n\\n"

        # Recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            content += "## 💡 Recommendations\\n\\n"
            for rec in recommendations:
                content += f"- {rec}\\n"
            content += "\\n"

        # Deprecated fields details
        deprecated_items = schema_analysis.get("deprecated_items", [])
        if deprecated_items:
            content += "## 📋 Deprecated Fields Details\\n\\n"
            for item in deprecated_items[:10]:  # Show first 10
                content += f"- **{item['type']}.{item['field']}:** {item['reason']}\\n"

            if len(deprecated_items) > 10:
                content += f"\\n*... and {len(deprecated_items) - 10} more*\\n"

        content += "\\n---\\n*Report generated by MonarchMoney Enhanced Schema Monitor*\\n"

        with open(output_file, 'w') as f:
            f.write(content)

    async def monitor_schema_changes(self, check_interval: int = 3600) -> None:
        """Continuously monitor schema for changes."""
        print(f"Starting continuous schema monitoring (checking every {check_interval} seconds)...")

        while True:
            try:
                print(f"[{datetime.now()}] Checking for schema changes...")

                # Get current schema
                current_schema = await self.monitor.introspect_schema()

                # Load previous schema if exists
                cache_file = self.monitor.cache_dir / "latest_schema.json"
                if cache_file.exists():
                    with open(cache_file) as f:
                        cache_data = json.load(f)
                        previous_schema = cache_data["schema"]

                    # Generate diff
                    diff = await self.monitor.diff_schemas(previous_schema, current_schema)
                    summary = diff.get("summary", {})

                    has_changes = any(summary[key] > 0 for key in summary if key != "timestamp")

                    if has_changes:
                        print(f"  🔔 Schema changes detected!")
                        print(f"    Types added: {summary['types_added']}")
                        print(f"    Types removed: {summary['types_removed']}")
                        print(f"    Types modified: {summary['types_modified']}")
                        print(f"    Fields removed: {summary['fields_removed']}")

                        # Save diff
                        diff_file = self.monitor.cache_dir / f"diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        with open(diff_file, 'w') as f:
                            json.dump(diff, f, indent=2)

                        print(f"    Diff saved to: {diff_file}")
                    else:
                        print("  ✅ No changes detected")

                # Save current schema
                await self.monitor.save_schema_history(current_schema)

                print(f"  Next check in {check_interval} seconds...")
                await asyncio.sleep(check_interval)

            except KeyboardInterrupt:
                print("\\n  Monitoring stopped by user")
                break
            except Exception as e:
                print(f"  ❌ Error during monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MonarchMoney GraphQL Schema Monitoring Tool"
    )

    parser.add_argument(
        "command",
        choices=["report", "monitor", "diff", "validate"],
        help="Command to execute"
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
        "--output",
        type=Path,
        default=Path.cwd() / "schema_reports",
        help="Output directory for reports"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Check interval for monitoring (seconds)"
    )

    args = parser.parse_args()

    # Initialize client
    print("Authenticating with MonarchMoney...")
    mm = MonarchMoney(debug=False)
    try:
        await mm.login_with_email(args.email, args.password)
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)

    # Initialize reporter
    reporter = SchemaReporter(mm)

    try:
        if args.command == "report":
            print("Generating comprehensive schema report...")
            report = await reporter.generate_comprehensive_report(args.output)
            print("✅ Report generation completed")

        elif args.command == "monitor":
            await reporter.monitor_schema_changes(args.interval)

        elif args.command == "validate":
            print("Validating current operations against schema...")
            # Add validation logic here

        elif args.command == "diff":
            print("Generating schema diff...")
            # Add diff logic here

    except Exception as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())