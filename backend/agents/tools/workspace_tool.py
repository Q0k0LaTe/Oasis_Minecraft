"""
Workspace Setup Tool - Creates mod directory structure

This tool creates the complete directory structure for a Fabric mod project.
"""
from pathlib import Path
from typing import Dict, Any


def setup_workspace(workspace_dir: Path, mod_id: str, package_name: str) -> Dict[str, Any]:
    """
    Create mod directory structure

    Args:
        workspace_dir: Base directory for the mod
        mod_id: Mod identifier (e.g., "my-mod")
        package_name: Java package name (e.g., "com.example.mymod")

    Returns:
        Dictionary with workspace_path
    """
    mod_dir = Path(workspace_dir) / mod_id
    package_path = package_name.replace(".", "/")

    # Main directories
    directories = [
        mod_dir / "gradle" / "wrapper",
        mod_dir / "src" / "main" / "java" / package_path / "item",
        mod_dir / "src" / "main" / "java" / package_path / "block",
        mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "lang",
        mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "items",
        mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "models" / "item",
        mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "models" / "block",
        mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "textures" / "item",
        mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "textures" / "block",
        mod_dir / "src" / "main" / "resources" / "assets" / mod_id / "blockstates",
        mod_dir / "src" / "main" / "resources" / "data" / mod_id / "recipe",
        mod_dir / "src" / "main" / "resources" / "data" / "minecraft" / "tags" / "block",
        mod_dir / "src" / "client" / "java" / package_path,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "workspace_path": str(mod_dir),
        "status": "success",
        "directories_created": len(directories)
    }


__all__ = ["setup_workspace"]
