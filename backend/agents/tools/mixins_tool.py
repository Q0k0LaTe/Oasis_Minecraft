"""
Mixins Tool - Generates mixins configuration file

This tool creates the mixins JSON configuration for Fabric.
"""
import json
from pathlib import Path
from typing import Dict, Any


def generate_mixins_json(
    workspace_path: Path,
    mod_id: str,
    package_name: str | None = None
) -> Dict[str, Any]:
    """
    Generate mixins configuration file

    Args:
        workspace_path: Mod directory path
        mod_id: Mod identifier
        package_name: Java package name

    Returns:
        Dictionary with path to generated file
    """
    mod_dir = Path(workspace_path)

    if not mod_id:
        raise ValueError("mod_id is required to generate mixins.json")
    if not package_name:
        package_name = f"com.example.{mod_id.replace('-', '_')}"

    mixins_config = {
        "required": True,
        "package": f"{package_name}.mixin",
        "compatibilityLevel": "JAVA_21",
        "mixins": [],
        "injectors": {
            "defaultRequire": 1
        }
    }

    mixins_path = mod_dir / "src" / "main" / "resources" / f"{mod_id}.mixins.json"
    mixins_path.write_text(json.dumps(mixins_config, indent=2))

    return {
        "status": "success",
        "mixins_json_path": str(mixins_path)
    }


__all__ = ["generate_mixins_json"]
