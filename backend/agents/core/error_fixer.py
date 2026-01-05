"""
Error Interpreter / Fixer

Responsibilities:
- Parse Gradle and validation errors
- Identify root causes
- Generate deterministic patches (not retries!)
- Apply fixes to workspace or spec

Key principle: Errors trigger PATCHES, not retries.
We fix the IR or workspace, not regenerate everything.
"""
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from agents.schemas import ModIR, SpecDelta


class ErrorFix(BaseModel):
    """A deterministic fix for an error"""
    error_type: str
    error_message: str
    fix_type: str  # patch_file, update_spec, add_dependency
    target_file: Optional[str] = None
    patch_content: Optional[str] = None
    spec_delta: Optional[SpecDelta] = None
    reasoning: str


class ErrorFixer:
    """
    Error Fixer - Deterministic error resolution

    Parses errors and generates patches.
    """

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)

    def analyze_error(self, error_output: str, error_type: str = "build") -> List[ErrorFix]:
        """
        Analyze error output and generate fixes

        Args:
            error_output: Error message or build log
            error_type: Type of error (build, validation, runtime)

        Returns:
            List of possible fixes
        """
        fixes = []

        # Parse different error types
        if error_type == "build":
            fixes.extend(self._parse_gradle_errors(error_output))
        elif error_type == "validation":
            fixes.extend(self._parse_validation_errors(error_output))

        return fixes

    def _parse_gradle_errors(self, output: str) -> List[ErrorFix]:
        """Parse Gradle build errors"""
        fixes = []

        # Common error patterns
        patterns = {
            r"cannot find symbol\s+symbol:\s+class\s+(\w+)": "missing_import",
            r"package\s+([\w.]+)\s+does not exist": "missing_package",
            r"incompatible types": "type_mismatch",
            r"';' expected": "syntax_error"
        }

        for pattern, error_type in patterns.items():
            matches = re.finditer(pattern, output, re.MULTILINE)
            for match in matches:
                fix = self._generate_fix(error_type, match)
                if fix:
                    fixes.append(fix)

        return fixes

    def _parse_validation_errors(self, output: str) -> List[ErrorFix]:
        """Parse validation errors"""
        fixes = []

        # Parse JSON from validation report
        # Look for common issues
        if "Duplicate registry ID" in output:
            # Extract ID and suggest rename
            pass

        return fixes

    def _generate_fix(self, error_type: str, match: re.Match) -> Optional[ErrorFix]:
        """Generate a fix for a specific error"""
        if error_type == "missing_import":
            class_name = match.group(1)
            return ErrorFix(
                error_type="missing_import",
                error_message=f"Missing import for {class_name}",
                fix_type="patch_file",
                reasoning=f"Add import statement for {class_name}",
                patch_content=f"import net.minecraft.{class_name};"
            )

        # More fix types to be implemented
        return None

    def apply_fixes(self, fixes: List[ErrorFix]) -> Dict[str, Any]:
        """
        Apply fixes to workspace

        Args:
            fixes: List of fixes to apply

        Returns:
            Application result
        """
        applied = []
        failed = []

        for fix in fixes:
            try:
                self._apply_single_fix(fix)
                applied.append(fix.error_type)
            except Exception as e:
                failed.append((fix.error_type, str(e)))

        return {
            "applied": len(applied),
            "failed": len(failed),
            "fixes": applied,
            "errors": failed
        }

    def _apply_single_fix(self, fix: ErrorFix):
        """Apply a single fix"""
        if fix.fix_type == "patch_file":
            # Apply file patch
            if fix.target_file and fix.patch_content:
                file_path = self.workspace_dir / fix.target_file
                # Apply patch (implementation needed)
                print(f"[ErrorFixer] Would patch {file_path}")

        elif fix.fix_type == "update_spec":
            # Generate spec delta
            if fix.spec_delta:
                print(f"[ErrorFixer] Would update spec: {fix.spec_delta}")

        elif fix.fix_type == "add_dependency":
            print(f"[ErrorFixer] Would add dependency")


# Import BaseModel
from pydantic import BaseModel


__all__ = ["ErrorFixer", "ErrorFix"]
