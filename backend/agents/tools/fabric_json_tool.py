"""
Fabric Mod JSON Tool - Generates fabric.mod.json metadata file

This tool creates the fabric.mod.json file required by Fabric Loader.
"""
import json
from pathlib import Path
from typing import Dict, Any, List

from config import (
    MINECRAFT_VERSION,
    FABRIC_LOADER_VERSION,
    JAVA_VERSION,
)


def generate_fabric_mod_json(
    workspace_path: Path,
    mod_id: str,
    mod_name: str,
    version: str,
    description: str,
    authors: List[str],
    license: str = "MIT",
    package_name: str = None,
    main_class_name: str = None
) -> Dict[str, Any]:
    """
    Generate fabric.mod.json metadata file

    Args:
        workspace_path: Mod directory path
        mod_id: Mod identifier
        mod_name: Human-readable mod name
        version: Mod version
        description: Mod description
        authors: List of author names
        license: License type
        package_name: Java package name
        main_class_name: Main class name

    Returns:
        Dictionary with path to generated file
    """
    mod_dir = Path(workspace_path)

    # Generate package and class names if not provided
    if not package_name:
        package_name = f"com.example.{mod_id.replace('-', '_')}"
    if not main_class_name:
        # Convert mod-id to ModId
        main_class_name = ''.join(word.capitalize() for word in mod_id.replace('_', '-').split('-'))

    fabric_mod = {
        "schemaVersion": 1,
        "id": mod_id,
        "version": "${version}",
        "name": mod_name,
        "description": description,
        "authors": authors,
        "contact": {},
        "license": license,
        "icon": f"assets/{mod_id}/icon.png",
        "environment": "*",
        "entrypoints": {
            "main": [f"{package_name}.{main_class_name}"],
            "client": [f"{package_name}.{main_class_name}Client"]
        },
        "mixins": [f"{mod_id}.mixins.json"],
        "depends": {
            "fabricloader": f">={FABRIC_LOADER_VERSION}",
            "minecraft": f"~{MINECRAFT_VERSION}",
            "java": f">={JAVA_VERSION}",
            "fabric-api": "*"
        }
    }

    fabric_mod_path = mod_dir / "src" / "main" / "resources" / "fabric.mod.json"
    fabric_mod_path.write_text(json.dumps(fabric_mod, indent=2))

    return {
        "status": "success",
        "fabric_mod_json_path": str(fabric_mod_path)
    }


__all__ = ["generate_fabric_mod_json"]
