"""
Builder - Gradle Compilation

Responsibilities:
- Run Gradle build
- Capture build output
- Report build status
- Extract compiled JAR

This wraps the existing Gradle compilation logic from mod_generator.py
"""
import subprocess
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable


class BuildError(Exception):
    """Raised when build fails"""
    pass


class Builder:
    """
    Builder - Compiles mod with Gradle

    Wraps Gradle build process.
    """

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)

    def build(
        self,
        mod_id: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Build mod with Gradle

        Args:
            mod_id: Mod identifier
            progress_callback: Optional callback for progress updates

        Returns:
            Build result with JAR path

        Raises:
            BuildError: If build fails
        """
        def log(msg: str):
            if progress_callback:
                progress_callback(msg)
            print(f"[Builder] {msg}")

        log("Starting Gradle build...")

        mod_dir = self.workspace_dir / mod_id

        if not mod_dir.exists():
            raise BuildError(f"Mod directory not found: {mod_dir}")

        # Ensure Gradle wrapper exists (copy from template if missing)
        wrapper_template_dir = Path(__file__).resolve().parents[2] / "templates" / "gradle_wrapper_template"
        if not (mod_dir / "gradlew").exists() and not (mod_dir / "gradlew.bat").exists():
            if wrapper_template_dir.exists():
                shutil.copytree(wrapper_template_dir, mod_dir, dirs_exist_ok=True)
                log("Gradle wrapper missing; copied from template.")
            else:
                log(f"Gradle wrapper template not found: {wrapper_template_dir}")

        # Run Gradle build
        try:
            gradle_cmd = ["./gradlew", "build", "--no-daemon"]
            if os.name == "nt":
                if (mod_dir / "gradlew.bat").exists():
                    gradle_cmd = [str(mod_dir / "gradlew.bat"), "build", "--no-daemon"]
                else:
                    gradle_cmd = ["gradle", "build", "--no-daemon"]
            elif (mod_dir / "gradlew").exists():
                gradle_cmd = [str(mod_dir / "gradlew"), "build", "--no-daemon"]
            log(f"Running: {' '.join(gradle_cmd)}")
            result = subprocess.run(
                gradle_cmd,
                cwd=mod_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                log(f"✗ Build failed with exit code {result.returncode}")
                log("STDOUT:" + result.stdout[-1000:])  # Last 1000 chars
                log("STDERR:" + result.stderr[-1000:])
                raise BuildError(f"Gradle build failed:\n{result.stderr}")

            log("✓ Build successful")

            # Find the JAR file
            jar_path = self._find_jar(mod_dir)

            return {
                "status": "success",
                "jar_path": str(jar_path),
                "build_log": result.stdout
            }

        except subprocess.TimeoutExpired:
            raise BuildError("Build timeout after 5 minutes")
        except Exception as e:
            raise BuildError(f"Build error: {str(e)}") from e

    def _find_jar(self, mod_dir: Path) -> Path:
        """Find the compiled JAR file"""
        libs_dir = mod_dir / "build" / "libs"

        if not libs_dir.exists():
            raise BuildError("Build libs directory not found")

        # Find JAR files (exclude -sources.jar)
        jar_files = [
            f for f in libs_dir.glob("*.jar")
            if not f.name.endswith("-sources.jar") and not f.name.endswith("-dev.jar")
        ]

        if not jar_files:
            raise BuildError("No JAR file found in build/libs")

        # Return the first (should be only one)
        return jar_files[0]


__all__ = ["Builder", "BuildError"]
