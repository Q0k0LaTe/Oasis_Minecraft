"""
Build Tool - Compiles mod using Gradle

This tool runs the Gradle build process to compile the mod and produce a JAR file.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import shutil


def build_mod(
    workspace_path: Path,
    mod_id: str,
    output_dir: Path = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Compile mod using Gradle and produce JAR file

    Args:
        workspace_path: Mod directory path
        mod_id: Mod identifier
        output_dir: Where to copy the final JAR (optional)
        progress_callback: Callback for progress updates

    Returns:
        Dictionary with build status and JAR path
    """
    mod_dir = Path(workspace_path)

    def log(msg: str):
        if progress_callback:
            progress_callback(msg)
        print(f"[Build] {msg}")

    try:
        # Determine gradlew command
        if (mod_dir / "gradlew").exists():
            gradle_cmd = "./gradlew"
        elif (mod_dir / "gradlew.bat").exists():
            gradle_cmd = "gradlew.bat"
        else:
            return {
                "status": "error",
                "error": "Gradle wrapper not found"
            }

        log("Running Gradle build...")

        # Run build
        result = subprocess.run(
            [gradle_cmd, "build", "--no-daemon"],
            cwd=mod_dir,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            log(f"Build failed with exit code {result.returncode}")
            return {
                "status": "error",
                "error": "Gradle build failed",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }

        log("Build successful!")

        # Find the generated JAR
        build_libs = mod_dir / "build" / "libs"
        jar_files = list(build_libs.glob("*.jar"))

        # Filter out sources JARs
        jar_files = [f for f in jar_files if "-sources" not in f.name and "-dev" not in f.name]

        if not jar_files:
            return {
                "status": "error",
                "error": "No JAR file found in build/libs"
            }

        jar_path = jar_files[0]
        log(f"Found JAR: {jar_path.name}")

        # Copy to output directory if specified
        final_jar_path = jar_path
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            final_jar_path = output_dir / f"{mod_id}.jar"
            shutil.copy(jar_path, final_jar_path)
            log(f"Copied JAR to: {final_jar_path}")

        return {
            "status": "success",
            "jar_path": str(final_jar_path),
            "build_output": result.stdout
        }

    except subprocess.TimeoutExpired:
        log("Build timed out after 10 minutes")
        return {
            "status": "error",
            "error": "Build timed out"
        }
    except Exception as e:
        log(f"Build error: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


__all__ = ["build_mod"]
