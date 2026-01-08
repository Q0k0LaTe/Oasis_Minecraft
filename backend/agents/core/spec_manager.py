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
import re
from pydantic import BaseModel

from agents.schemas import ModSpec, SpecDelta, normalize_creative_tab


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

    def __init__(self, workspace_dir: Optional[Path] = None, spec_dir: Optional[Path] = None):
        """
        Initialize Spec Manager

        Args:
            workspace_dir: Base workspace directory (used to derive spec_dir if provided)
            spec_dir: Optional explicit directory to store spec files
        """
        if workspace_dir is None and spec_dir is None:
            raise ValueError("workspace_dir or spec_dir must be provided")

        self.workspace_dir = Path(workspace_dir) if workspace_dir else None
        self.spec_dir = Path(spec_dir) if spec_dir else Path(workspace_dir) / "spec"
        self.spec_dir.mkdir(parents=True, exist_ok=True)

        self.current_spec_path = self.spec_dir / "mod_spec.json"
        self.spec_file = self.current_spec_path
        self.history_dir = self.spec_dir / "history"
        self.history_dir.mkdir(exist_ok=True)

        self._current_spec: Optional[ModSpec] = None
        self._version_counter = self._load_version_counter()

    def initialize_spec(self, initial_spec: ModSpec) -> str:
        """
        Initialize a new spec

        Args:
            initial_spec: Initial mod specification

        Returns:
            Version ID
        """
        self._current_spec = initial_spec
        if not self._current_spec.version:
            self._current_spec.version = "1.0.0"
        version_id = self._save_version(None, "Initial specification")
        return version_id

    def load_current_spec(self) -> Optional[ModSpec]:
        """Load the current spec from disk"""
        if self.current_spec_path.exists():
            spec_data = json.loads(self.current_spec_path.read_text())
            self._current_spec = self._normalize_and_build_spec(spec_data)
            return self._current_spec
        return None

    def get_current_spec(self) -> Optional[ModSpec]:
        """Get the current spec (from memory or disk)"""
        if self._current_spec is None:
            return self.load_current_spec()

        # Ensure in-memory spec is normalized (handles legacy CreativeTab values)
        normalized = self._normalize_and_build_spec(self._current_spec.model_dump())
        self._current_spec = normalized
        return normalized

    def apply_delta(self, delta: SpecDelta) -> ModSpec:
        """
        Apply a delta to the current spec

        Args:
            delta: Spec delta to apply

        Returns:
            Updated ModSpec

        Raises:
            ValueError: If delta cannot be applied
        """
        # Ensure the current spec is loaded if it exists on disk
        if self._current_spec is None:
            self.load_current_spec()

        if delta.is_structured():
            if self._current_spec is None:
                raise ValueError("No current spec loaded. Initialize first.")
            new_spec = self._apply_structured_delta(self._current_spec, delta)
            new_spec.version = self._next_version(delta, self._current_spec.version)
            notes = f"{delta.operation or 'update'} at {delta.path or 'root'}"
        else:
            new_spec = self._apply_semantic_delta(delta)
            notes = f"{(delta.delta_type or 'update').capitalize()} delta"

        self._current_spec = new_spec
        self._save_version(delta, notes)

        return self._current_spec

    def _normalize_and_build_spec(self, data: Dict[str, Any]) -> ModSpec:
        """Normalize legacy/invalid values before constructing ModSpec."""
        # Normalize creative tabs for items/blocks/tools
        for key in ("items", "blocks", "tools"):
            entries = data.get(key, [])
            for entry in entries:
                if isinstance(entry, dict) and "creative_tab" in entry:
                    entry["creative_tab"] = normalize_creative_tab(entry["creative_tab"]).value
        return ModSpec(**data)

    def _apply_structured_delta(self, spec: ModSpec, delta: SpecDelta) -> ModSpec:
        """
        Apply a structured JSON-path delta to a spec.
        """
        if not delta.path:
            raise ValueError("Structured deltas require a path")

        spec_dict = spec.model_dump()

        path_parts = self._parse_path(delta.path)

        if delta.operation == "add":
            value = delta.value
            if path_parts and path_parts[-1] == "creative_tab":
                value = normalize_creative_tab(delta.value).value

            # For arrays (items, blocks, tools), append to the end
            if len(path_parts) >= 2 and path_parts[0] in ("items", "blocks", "tools"):
                array_name = path_parts[0]
                # If path is like "items[N]" where N is the next index, append
                if len(path_parts) == 2 and path_parts[1].isdigit():
                    idx = int(path_parts[1])
                    if idx == len(spec_dict[array_name]):
                        # Appending to end
                        spec_dict[array_name].append(value)
                    else:
                        # Inserting at specific index
                        self._set_nested_value(spec_dict, path_parts, value)
                else:
                    # Path like "items[N].property", set the nested value
                    self._set_nested_value(spec_dict, path_parts, value)
            else:
                # For non-array fields, just set the value
                self._set_nested_value(spec_dict, path_parts, value)

        elif delta.operation == "update":
            # Update requires the path to exist
            if not self._path_exists(spec_dict, path_parts):
                raise ValueError(f"Cannot update non-existent path: {delta.path}")

            value = delta.value
            if path_parts and path_parts[-1] == "creative_tab":
                value = normalize_creative_tab(delta.value).value
            self._set_nested_value(spec_dict, path_parts, value)

        elif delta.operation == "remove":
            self._remove_nested_value(spec_dict, path_parts)
        else:
            raise ValueError(f"Unknown operation: {delta.operation}")

        return ModSpec(**spec_dict)

    def _apply_semantic_delta(self, delta: SpecDelta) -> ModSpec:
        """
        Apply a semantic create/update delta (legacy style used in tests).
        """
        delta_type = (delta.delta_type or ("create" if self._current_spec is None else "update")).lower()

        if delta_type == "create":
            spec = self._create_spec_from_delta(delta)
            spec.version = delta.version or spec.version or "1.0.0"
            return spec

        if delta_type == "update":
            base_spec = self._current_spec or self.load_current_spec()
            if base_spec is None:
                base_spec = self._create_spec_from_delta(delta)
            else:
                base_spec = self._update_spec_from_delta(base_spec, delta)

            base_spec.version = self._next_version(delta, base_spec.version)
            return base_spec

        raise ValueError(f"Unknown delta_type: {delta_type}")

    def _create_spec_from_delta(self, delta: SpecDelta) -> ModSpec:
        """Create a new ModSpec from a create delta."""
        mod_name = delta.mod_name or "New Mod"
        mod_id = delta.mod_id or self._generate_mod_id(mod_name)

        return ModSpec(
            mod_name=mod_name,
            mod_id=mod_id,
            version=delta.version or "1.0.0",
            author=delta.author or "Unknown",
            description=delta.description or "",
            items=list(delta.items_to_add or []),
            blocks=list(delta.blocks_to_add or []),
            tools=list(delta.tools_to_add or [])
        )

    def _update_spec_from_delta(self, current_spec: ModSpec, delta: SpecDelta) -> ModSpec:
        """Update an existing ModSpec using a semantic delta."""
        spec_data = current_spec.model_dump()

        if delta.mod_name:
            spec_data["mod_name"] = delta.mod_name
        if delta.mod_id:
            spec_data["mod_id"] = delta.mod_id
        if delta.author:
            spec_data["author"] = delta.author
        if delta.description:
            spec_data["description"] = delta.description
        if delta.minecraft_version:
            spec_data["minecraft_version"] = delta.minecraft_version
        if delta.fabric_loader_version:
            spec_data["fabric_loader_version"] = delta.fabric_loader_version
        if delta.fabric_api_version:
            spec_data["fabric_api_version"] = delta.fabric_api_version

        updated_spec = ModSpec(**spec_data)

        if delta.items_to_add:
            updated_spec.items.extend(delta.items_to_add)
        if delta.blocks_to_add:
            updated_spec.blocks.extend(delta.blocks_to_add)
        if delta.tools_to_add:
            updated_spec.tools.extend(delta.tools_to_add)

        # Preserve provided version if set; actual bump handled by caller
        if delta.version:
            updated_spec.version = delta.version

        return updated_spec

    def _next_version(self, delta: SpecDelta, current_version: Optional[str]) -> str:
        """Determine the next version string after applying a delta."""
        if delta.version:
            return delta.version
        return self._bump_version(current_version)

    def _bump_version(self, version: Optional[str]) -> str:
        """Increment a semantic version string (patch component)."""
        if not version:
            return "0.0.1"

        parts = version.split(".")
        try:
            while len(parts) < 3:
                parts.append("0")
            major, minor, patch = [int(p) for p in parts[:3]]
            patch += 1
            return f"{major}.{minor}.{patch}"
        except ValueError:
            raise ValueError(f"Invalid version '{version}' - cannot auto-bump non-numeric values")

    def _generate_mod_id(self, mod_name: str) -> str:
        """Generate a mod_id from a mod name."""
        mod_id = mod_name.lower()
        mod_id = re.sub(r'[^a-z0-9_]', '_', mod_id)
        mod_id = re.sub(r'_+', '_', mod_id).strip('_')
        return mod_id or "custom_mod"

    def _parse_path(self, path: str) -> List[str]:
        """
        Parse a JSON path into parts

        Examples:
            "mod_name" → ["mod_name"]
            "items[0].rarity" → ["items", "0", "rarity"]
            "blocks[1].properties.hardness" → ["blocks", "1", "properties", "hardness"]
        """
        # Replace [N] with .N for easier splitting
        path = re.sub(r'\[(\d+)\]', r'.\1', path)
        return path.split('.')

    def _path_exists(self, data: Dict, path_parts: List[str]) -> bool:
        """Check if a path exists in the data structure"""
        try:
            current = data
            for part in path_parts:
                if part.isdigit():
                    idx = int(part)
                    if isinstance(current, list):
                        if idx >= len(current):
                            return False
                        current = current[idx]
                    else:
                        return False
                else:
                    if part not in current:
                        return False
                    current = current[part]
            return True
        except (KeyError, IndexError, TypeError):
            return False

    def _set_nested_value(self, data: Dict, path_parts: List[str], value: Any):
        """Set a value at a nested path"""
        current = data
        for i, part in enumerate(path_parts[:-1]):
            if part.isdigit():
                # Array index - extend list if needed
                idx = int(part)
                if isinstance(current, list):
                    # Determine what type of object to create based on next part
                    next_part = path_parts[i + 1] if i + 1 < len(path_parts) else None
                    while len(current) <= idx:
                        # Create appropriate structure for the new element
                        if next_part and next_part.isdigit():
                            current.append([])
                        else:
                            current.append({})
                current = current[idx]
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
            idx = int(final_key)
            if isinstance(current, list):
                # Extend list if needed
                while len(current) <= idx:
                    current.append(None)
                current[idx] = value
            else:
                current[idx] = value
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

    def _load_version_counter(self) -> int:
        """Initialize version counter based on existing history files."""
        counters = []
        for version_file in self.history_dir.glob("v*.json"):
            try:
                counters.append(int(version_file.stem.lstrip("v")))
            except ValueError:
                continue
        return max(counters, default=0)

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
        if self._current_spec is None:
            raise ValueError("No current spec to save")

        spec_dict = self._current_spec.model_dump()
        self.current_spec_path.write_text(json.dumps(spec_dict, indent=2))

        # Save version history
        spec_hash = self._hash_spec(spec_dict)
        history_entry = {
            "version": version_id,
            "timestamp": timestamp.isoformat(),
            "spec_hash": spec_hash,
            "notes": notes,
            "delta": delta.model_dump(exclude_none=True) if delta else None,
            "spec": spec_dict
        }

        history_file = self.history_dir / f"{version_id}.json"
        history_file.write_text(json.dumps(history_entry, indent=2))

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

# Export
__all__ = ["SpecManager", "SpecVersion"]
