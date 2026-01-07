"""
Gradle Wrapper Tool - Copies Gradle wrapper files to project

This tool sets up the Gradle wrapper in the mod project.
"""
import shutil
from pathlib import Path
from typing import Dict, Any


def setup_gradle_wrapper(workspace_path: Path) -> Dict[str, Any]:
    """
    Copy Gradle wrapper files to project

    Args:
        workspace_path: Mod directory path

    Returns:
        Dictionary with paths to gradle wrapper files
    """
    mod_dir = Path(workspace_path)
    templates_dir = Path(__file__).parent.parent.parent / "templates"

    # Copy gradle wrapper directory
    wrapper_src = templates_dir / "gradle" / "wrapper"
    wrapper_dst = mod_dir / "gradle" / "wrapper"

    if wrapper_src.exists():
        wrapper_dst.mkdir(parents=True, exist_ok=True)
        for item in wrapper_src.iterdir():
            if item.is_file():
                shutil.copy(item, wrapper_dst / item.name)

    # Copy gradlew scripts
    for script in ["gradlew", "gradlew.bat"]:
        script_src = templates_dir / script
        if script_src.exists():
            script_dst = mod_dir / script
            shutil.copy(script_src, script_dst)
            # Make executable on Unix
            if script == "gradlew":
                script_dst.chmod(0o755)

    return {
        "status": "success",
        "gradle_wrapper_path": str(wrapper_dst)
    }


__all__ = ["setup_gradle_wrapper"]
