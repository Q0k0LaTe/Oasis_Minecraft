"""
Main Pipeline - Orchestrates the complete mod generation flow

This module wires together all pipeline components:
Orchestrator → SpecManager → Compiler → Planner → Executor → Validator → Builder → ErrorFixer

Usage:
    pipeline = ModGenerationPipeline(job_id="job123")
    result = pipeline.generate_mod(user_prompt="Create a ruby gem item")
"""
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import traceback

from config import GENERATED_DIR, DOWNLOADS_DIR

# Import core components
from agents.core.orchestrator import Orchestrator
from agents.core.spec_manager import SpecManager
from agents.core.compiler import Compiler
from agents.core.planner import Planner
from agents.core.executor import Executor
from agents.core.validator import Validator
from agents.core.builder import Builder
from agents.core.error_fixer import ErrorFixer

# Import tool registry
from agents.tools.tool_registry import create_tool_registry


class PipelineError(Exception):
    """Raised when pipeline execution fails"""
    pass


class ModGenerationPipeline:
    """
    Complete mod generation pipeline

    This class orchestrates the entire flow from user prompt to compiled mod.
    """

    def __init__(
        self,
        job_id: str,
        workspace_dir: Optional[Path] = None,
        downloads_dir: Optional[Path] = None
    ):
        """
        Initialize pipeline

        Args:
            job_id: Unique job identifier
            workspace_dir: Base directory for generation (defaults to GENERATED_DIR/job_id)
            downloads_dir: Directory for final JARs (defaults to DOWNLOADS_DIR)
        """
        self.job_id = job_id
        self.workspace_dir = workspace_dir or (GENERATED_DIR / job_id)
        self.downloads_dir = downloads_dir or DOWNLOADS_DIR

        # Ensure directories exist
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.orchestrator = Orchestrator()
        self.spec_manager = SpecManager(self.workspace_dir)
        self.compiler = Compiler()
        self.planner = Planner()
        self.validator = Validator()
        self.builder = Builder(self.workspace_dir)
        self.error_fixer = ErrorFixer()

        # Execution log
        self.execution_log = []

    def generate_mod(
        self,
        user_prompt: str,
        conversation_history: list = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Generate a mod from user prompt

        This is the main entry point for mod generation.

        Args:
            user_prompt: User's request/prompt
            conversation_history: Previous conversation messages
            progress_callback: Optional callback for progress updates (msg: str) -> None

        Returns:
            Dictionary with generation results including JAR path

        Raises:
            PipelineError: If generation fails
        """
        def log(msg: str):
            self.execution_log.append(msg)
            if progress_callback:
                progress_callback(msg)
            print(f"[Pipeline {self.job_id}] {msg}")

        try:
            log("=== Starting Mod Generation Pipeline ===")
            log(f"Prompt: {user_prompt}")

            # Phase 1: Orchestrator - Convert prompt to SpecDelta
            log("Phase 1: Converting prompt to specification delta...")
            orchestrator_response = self.orchestrator.process_prompt(
                user_prompt=user_prompt,
                current_spec=None,
                context=None  # TODO: Build context from conversation_history
            )
            log(f"✓ Generated {len(orchestrator_response.deltas)} deltas")
            if orchestrator_response.requires_user_input:
                log(f"⚠ Clarifying questions: {orchestrator_response.clarifying_questions}")

            # Phase 2: SpecManager - Apply deltas and get current spec
            log("Phase 2: Applying deltas to mod specification...")

            # Initialize spec if this is a new mod
            existing_spec = self.spec_manager.get_current_spec()
            if existing_spec is None:
                from agents.schemas import ModSpec
                log("Initializing new mod specification...")
                base_spec = ModSpec(mod_name="New Mod")
                self.spec_manager.initialize_spec(base_spec)

            # Apply all deltas
            current_spec = None
            for spec_delta in orchestrator_response.deltas:
                current_spec = self.spec_manager.apply_delta(spec_delta)

            log(f"✓ Current spec version: {current_spec.version}")
            log(f"  - Mod: {current_spec.mod_name} (v{current_spec.version})")
            log(f"  - Items: {len(current_spec.items)}, Blocks: {len(current_spec.blocks)}")

            # Phase 3: Compiler - Transform Spec → IR
            log("Phase 3: Compiling specification to intermediate representation...")
            mod_ir = self.compiler.compile(current_spec)
            log(f"✓ Generated IR with {len(mod_ir.items)} items, {len(mod_ir.blocks)} blocks")
            log(f"  - Base package: {mod_ir.base_package}")
            log(f"  - Main class: {mod_ir.main_class_name}")

            # Phase 4: Planner - Convert IR → Task DAG
            log("Phase 4: Planning execution tasks...")
            task_dag = self.planner.plan(mod_ir, workspace_root=self.workspace_dir)
            log(f"✓ Generated execution plan with {task_dag.total_tasks} tasks")

            # Phase 5: Executor - Run tasks
            log("Phase 5: Executing tasks...")
            workspace_root = self.workspace_dir
            mod_workspace = workspace_root / mod_ir.mod_id

            # Create tool registry for this workspace
            tool_registry = create_tool_registry(workspace_root)

            # Create executor
            executor = Executor(
                workspace_dir=workspace_root,
                tool_registry=tool_registry
            )

            # Execute task DAG
            exec_result = executor.execute(task_dag, progress_callback=log)
            log(f"✓ Execution complete: {exec_result['completed_tasks']}/{exec_result['total_tasks']} tasks")

            # Phase 6: Validator - Pre-build validation
            log("Phase 6: Validating generated files...")
            try:
                validation_result = self.validator.validate(ir=mod_ir)
                log(f"✓ Validation passed ({validation_result['warnings']} warnings)")
            except Exception as e:
                log(f"⚠ Validation found issues: {str(e)}")
                log("⚠ Proceeding to build anyway...")
                # Note: In production, you might want to halt here
                # For now, we'll attempt the build and let Gradle catch issues

            # Phase 7: Builder - Compile with Gradle
            log("Phase 7: Building mod with Gradle (this may take 1-2 minutes)...")
            build_result = self.builder.build(
                mod_id=mod_ir.mod_id,
                progress_callback=log
            )

            if build_result["status"] == "success":
                jar_path = build_result["jar_path"]
                log(f"✓ Build successful: {Path(jar_path).name}")

                # Copy JAR to downloads directory
                import shutil
                final_jar_path = self.downloads_dir / f"{mod_ir.mod_id}.jar"
                shutil.copy(jar_path, final_jar_path)
                log(f"Copied JAR to: {final_jar_path.name}")
                jar_path = str(final_jar_path)
            else:
                log("✗ Build failed")
                error_msg = build_result.get("error", "Unknown error")
                log(f"Error: {error_msg}")

                # Show build errors
                if build_result.get("stderr"):
                    log("Build output:")
                    for line in build_result["stderr"].split('\n')[-10:]:
                        if line.strip():
                            log(f"  {line}")

                raise PipelineError(f"Build failed: {error_msg}")

            # Success!
            log("=== Mod Generation Complete ===")

            return {
                "status": "success",
                "job_id": self.job_id,
                "mod_id": mod_ir.mod_id,
                "mod_name": mod_ir.mod_name,
                "jar_path": jar_path,
                "spec_version": current_spec.version,
                "workspace_path": str(mod_workspace),
                "execution_log": self.execution_log
            }

        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            log(f"✗ {error_msg}")
            log(f"Traceback: {traceback.format_exc()}")

            return {
                "status": "error",
                "error": error_msg,
                "traceback": traceback.format_exc(),
                "execution_log": self.execution_log
            }

    def get_current_spec(self) -> Optional[Dict[str, Any]]:
        """Get current mod specification"""
        spec = self.spec_manager.get_current_spec()
        if spec:
            return spec.model_dump()
        return None

    def get_execution_log(self) -> list:
        """Get execution log"""
        return self.execution_log.copy()


# Convenience function for simple usage
def generate_mod_from_prompt(
    user_prompt: str,
    job_id: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Generate a mod from a user prompt (convenience function)

    Args:
        user_prompt: User's request
        job_id: Unique job identifier
        progress_callback: Optional progress callback

    Returns:
        Generation result dictionary
    """
    pipeline = ModGenerationPipeline(job_id=job_id)
    return pipeline.generate_mod(
        user_prompt=user_prompt,
        progress_callback=progress_callback
    )


__all__ = [
    "ModGenerationPipeline",
    "generate_mod_from_prompt",
    "PipelineError"
]
