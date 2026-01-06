"""
Spec Manager - Maintains Canonical Mod Specification

Responsibilities:
- Persist mod_spec.json
- Apply spec deltas deterministically
- Track versions and diffs
- Provide spec history/audit trail

This component owns the "source of truth" for user intent.
"""
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
from pydantic import BaseModel

from agents.schemas import ModSpec, SpecDelta


class SpecVersion(BaseModel):
    """A versioned snapshot of the spec"""
    version: str
    spec: ModSpec
    timestamp: datetime
    spec_hash: str
    delta_applied: Optional[SpecDelta] = None
    notes: Optional[str] = None


class SpecManager:
    """Manages the canonical mod specification with versioning"""

    def __init__(self, workspace_dir: Path):
        """
        Initialize Spec Manager

        Args:
            workspace_dir: Directory to store spec files
        """
        self.workspace_dir = Path(workspace_dir)
        self.spec_dir = self.workspace_dir / "spec"
        self.spec_dir.mkdir(parents=True, exist_ok=True)

        self.current_spec_path = self.spec_dir / "mod_spec.json"
        self.history_dir = self.spec_dir / "history"
        self.history_dir.mkdir(exist_ok=True)

        self._current_spec: Optional[ModSpec] = None
        self._version_counter = 0

    def initialize_spec(self, initial_spec: ModSpec) -> str:
        """
        Initialize a new spec

        Args:
            initial_spec: Initial mod specification

        Returns:
            Version ID
        """
        self._current_spec = initial_spec
        version_id = self._save_version(None, "Initial specification")
        return version_id

    def load_current_spec(self) -> Optional[ModSpec]:
        """Load the current spec from disk"""
        if self.current_spec_path.exists():
            with open(self.current_spec_path, 'r') as f:
                spec_data = json.load(f)
                self._current_spec = ModSpec(**spec_data)
                return self._current_spec
        return None

    def get_current_spec(self) -> Optional[ModSpec]:
        """Get the current spec (from memory or disk)"""
        if self._current_spec is None:
            return self.load_current_spec()
        return self._current_spec

    def apply_delta(self, delta: SpecDelta) -> str:
        """
        Apply a delta to the current spec

        Args:
            delta: Spec delta to apply

        Returns:
            New version ID

        Raises:
            ValueError: If delta cannot be applied
        """
        if self._current_spec is None:
            raise ValueError("No current spec loaded. Initialize first.")

        # Apply delta to create new spec
        new_spec = self._apply_delta_to_spec(self._current_spec, delta)

        # Validate new spec
        # (Pydantic validation happens automatically)

        # Save and version
        self._current_spec = new_spec
        version_id = self._save_version(delta, f"{delta.operation} at {delta.path}")

        return version_id

    def _apply_delta_to_spec(self, spec: ModSpec, delta: SpecDelta) -> ModSpec:
        """
        Apply a single delta to a spec

        Args:
            spec: Current spec
            delta: Delta to apply

        Returns:
            New spec with delta applied
        """
        # Convert spec to dict for manipulation
        spec_dict = spec.dict()

        # Parse path (e.g., "items[0].rarity" or "mod_name")
        path_parts = self._parse_path(delta.path)

        if delta.operation == "add":
            self._set_nested_value(spec_dict, path_parts, delta.value)
        elif delta.operation == "update":
            self._set_nested_value(spec_dict, path_parts, delta.value)
        elif delta.operation == "remove":
            self._remove_nested_value(spec_dict, path_parts)
        else:
            raise ValueError(f"Unknown operation: {delta.operation}")

        # Create new spec from modified dict
        return ModSpec(**spec_dict)

    def _parse_path(self, path: str) -> List[str]:
        """
        Parse a JSON path into parts

        Examples:
            "mod_name" → ["mod_name"]
            "items[0].rarity" → ["items", "0", "rarity"]
            "blocks[1].properties.hardness" → ["blocks", "1", "properties", "hardness"]
        """
        import re
        # Replace [N] with .N for easier splitting
        path = re.sub(r'\[(\d+)\]', r'.\1', path)
        return path.split('.')

    def _set_nested_value(self, data: Dict, path_parts: List[str], value: Any):
        """Set a value at a nested path"""
        current = data
        for i, part in enumerate(path_parts[:-1]):
            if part.isdigit():
                # Array index
                current = current[int(part)]
            else:
                # Object key
                if part not in current:
                    # Create intermediate object/array
                    next_part = path_parts[i + 1]
                    current[part] = [] if next_part.isdigit() else {}
                current = current[part]

        # Set the final value
        final_key = path_parts[-1]
        if final_key.isdigit():
            current[int(final_key)] = value
        else:
            current[final_key] = value

    def _remove_nested_value(self, data: Dict, path_parts: List[str]):
        """Remove a value at a nested path"""
        current = data
        for part in path_parts[:-1]:
            if part.isdigit():
                current = current[int(part)]
            else:
                current = current[part]

        final_key = path_parts[-1]
        if final_key.isdigit():
            del current[int(final_key)]
        else:
            del current[final_key]

    def _save_version(self, delta: Optional[SpecDelta], notes: str) -> str:
        """
        Save current spec as a new version

        Args:
            delta: Delta that was applied (None for initial)
            notes: Version notes

        Returns:
            Version ID
        """
        self._version_counter += 1
        version_id = f"v{self._version_counter}"
        timestamp = datetime.utcnow()

        # Save current spec
        spec_dict = self._current_spec.dict()
        with open(self.current_spec_path, 'w') as f:
            json.dump(spec_dict, f, indent=2)

        # Save version history
        spec_hash = self._hash_spec(spec_dict)
        history_entry = {
            "version": version_id,
            "timestamp": timestamp.isoformat(),
            "spec_hash": spec_hash,
            "notes": notes,
            "delta": delta.dict() if delta else None,
            "spec": spec_dict
        }

        history_file = self.history_dir / f"{version_id}.json"
        with open(history_file, 'w') as f:
            json.dump(history_entry, f, indent=2)

        return version_id

    def _hash_spec(self, spec_dict: Dict) -> str:
        """Compute hash of spec for change detection"""
        spec_str = json.dumps(spec_dict, sort_keys=True)
        return hashlib.sha256(spec_str.encode()).hexdigest()[:16]

    def get_version_history(self) -> List[Dict[str, Any]]:
        """Get list of all spec versions"""
        history = []
        for version_file in sorted(self.history_dir.glob("v*.json")):
            with open(version_file, 'r') as f:
                history.append(json.load(f))
        return history

    def rollback_to_version(self, version_id: str) -> ModSpec:
        """
        Rollback to a previous version

        Args:
            version_id: Version to roll back to (e.g., "v3")

        Returns:
            The rolled-back spec

        Raises:
            FileNotFoundError: If version doesn't exist
        """
        version_file = self.history_dir / f"{version_id}.json"
        if not version_file.exists():
            raise FileNotFoundError(f"Version {version_id} not found")

        with open(version_file, 'r') as f:
            version_data = json.load(f)

        self._current_spec = ModSpec(**version_data["spec"])
        self._save_version(None, f"Rollback to {version_id}")

        return self._current_spec


# Need to import BaseModel
from pydantic import BaseModel

# Export
__all__ = ["SpecManager", "SpecVersion"]
