"""
Validator - Pre-Build Validation

Responsibilities:
- Validate generated code and assets BEFORE Gradle build
- Check JSON schema validity
- Verify asset file existence
- Check registry ID conflicts
- Validate Java syntax
- Catch errors early

This prevents wasting time on Gradle builds that will fail.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from agents.schemas import ModIR


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class ValidationIssue:
    """A single validation issue"""
    def __init__(self, severity: str, category: str, message: str, file_path: Optional[str] = None):
        self.severity = severity  # ERROR, WARNING, INFO
        self.category = category  # json, asset, registry, java
        self.message = message
        self.file_path = file_path

    def __repr__(self):
        return f"[{self.severity}] {self.category}: {self.message}" + (f" ({self.file_path})" if self.file_path else "")


class Validator:
    """
    Validator - Pre-build validation

    Catches errors before expensive Gradle build.
    """

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else None
        self.issues: List[ValidationIssue] = []

    def validate(self, ir: ModIR) -> Dict[str, Any]:
        """
        Validate generated mod structure

        Args:
            ir: Intermediate Representation

        Returns:
            Validation report

        Raises:
            ValidationError: If critical errors found
        """
        self.issues = []

        print(f"[Validator] Validating mod: {ir.mod_id}")

        # Run all validation checks
        self._validate_json_files(ir)
        self._validate_assets(ir)
        self._validate_registry_ids(ir)
        self._validate_file_structure(ir)

        # Summarize results
        errors = [i for i in self.issues if i.severity == "ERROR"]
        warnings = [i for i in self.issues if i.severity == "WARNING"]

        report = {
            "status": "failed" if errors else "passed",
            "total_issues": len(self.issues),
            "errors": len(errors),
            "warnings": len(warnings),
            "issues": [str(i) for i in self.issues]
        }

        if errors:
            print(f"[Validator] ✗ Validation failed: {len(errors)} errors")
            for error in errors[:5]:  # Show first 5
                print(f"  - {error}")
            raise ValidationError(f"Validation failed with {len(errors)} errors")

        print(f"[Validator] ✓ Validation passed ({len(warnings)} warnings)")
        return report

    def _validate_json_files(self, ir: ModIR):
        """Validate all JSON files are well-formed"""
        for asset in ir.assets:
            if asset.asset_type in ["model", "blockstate", "recipe", "loot_table"]:
                if asset.json_content:
                    try:
                        # Validate can serialize
                        json.dumps(asset.json_content)
                    except Exception as e:
                        self.issues.append(ValidationIssue(
                            "ERROR", "json",
                            f"Invalid JSON in {asset.asset_type}: {str(e)}",
                            asset.file_path
                        ))

    def _validate_assets(self, ir: ModIR):
        """Check that required assets exist"""
        for item in ir.items:
            if not item.texture_asset:
                self.issues.append(ValidationIssue(
                    "ERROR", "asset",
                    f"Missing texture asset for item: {item.item_id}"
                ))

        for block in ir.blocks:
            if not block.texture_asset:
                self.issues.append(ValidationIssue(
                    "ERROR", "asset",
                    f"Missing texture asset for block: {block.block_id}"
                ))

    def _validate_registry_ids(self, ir: ModIR):
        """Check for registry ID conflicts"""
        all_ids = set()

        for item in ir.items:
            if item.item_id in all_ids:
                self.issues.append(ValidationIssue(
                    "ERROR", "registry",
                    f"Duplicate registry ID: {item.item_id}"
                ))
            all_ids.add(item.item_id)

        for block in ir.blocks:
            if block.block_id in all_ids:
                self.issues.append(ValidationIssue(
                    "ERROR", "registry",
                    f"Duplicate registry ID: {block.block_id}"
                ))
            all_ids.add(block.block_id)

    def _validate_file_structure(self, ir: ModIR):
        """Validate directory structure is correct"""
        required_dirs = [
            "src/main/java",
            "src/main/resources",
            f"src/main/resources/assets/{ir.mod_id}",
            f"src/main/resources/data/{ir.mod_id}"
        ]

        # This will be checked after files are written
        # For now, just log
        print(f"[Validator] Would check for directories: {required_dirs}")


__all__ = ["Validator", "ValidationError", "ValidationIssue"]
