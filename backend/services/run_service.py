"""
Run Service - Background task execution for runs

Handles:
- Generation runs (user message → AI generates spec delta → build)
- Build runs (compile current spec to JAR)
- Event emission during execution
"""
import traceback
from datetime import datetime
from pathlib import Path
from uuid import UUID
from typing import Optional, Dict, Any

from database import SessionLocal, Run, Workspace, Message, Artifact, SpecHistory
from services.event_service import (
    emit_event_sync,
    EventType,
)
from config import GENERATED_DIR, DOWNLOADS_DIR


def execute_run(run_id: str):
    """
    Execute a generation run in background
    
    This is called from the conversations router when a user sends a message
    with trigger_run=True.
    
    Flow:
    1. Load run and workspace
    2. Get user message content
    3. Call AI to generate spec delta (placeholder for now)
    4. Apply delta to spec
    5. Optionally trigger build
    6. Create assistant message with result
    """
    db = SessionLocal()
    
    try:
        run_uuid = UUID(run_id)
        run = db.query(Run).filter(Run.id == run_uuid).first()
        
        if not run:
            print(f"[RunService] Run {run_id} not found")
            return
        
        workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
        if not workspace:
            _fail_run(db, run, "Workspace not found")
            return
        
        # Update run status to running
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()
        
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {"status": "running"})
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Starting generation run...", "level": "info"})
        
        # Get trigger message
        trigger_message = None
        if run.trigger_message_id:
            trigger_message = db.query(Message).filter(Message.id == run.trigger_message_id).first()
        
        user_prompt = trigger_message.content if trigger_message else "Generate a mod"
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": f"Processing: {user_prompt[:100]}...", "level": "info"})
        
        # ====================================================================
        # AI Generation (Placeholder - Agent team will implement)
        # ====================================================================
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Phase 1: Analyzing prompt...", "level": "info"})
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 10})
        
        # Placeholder: Generate a simple spec delta
        # In the real implementation, this will call the Orchestrator
        spec_delta = _generate_spec_delta_placeholder(user_prompt)
        
        emit_event_sync(db, run.id, EventType.SPEC_PREVIEW, {"delta": spec_delta})
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Phase 2: Applying spec changes...", "level": "info"})
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 30})
        
        # Apply delta to workspace spec
        current_spec = workspace.spec or {}
        new_spec = _apply_spec_delta_placeholder(current_spec, spec_delta)
        
        # Save spec
        workspace.spec = new_spec
        workspace.spec_version += 1
        workspace.last_modified_at = datetime.utcnow()
        
        # Save to history
        history = SpecHistory(
            workspace_id=workspace.id,
            version=workspace.spec_version,
            spec=new_spec,
            delta=spec_delta,
            change_source="ai",
            change_notes=f"Generated from: {user_prompt[:50]}..."
        )
        db.add(history)
        db.commit()
        
        emit_event_sync(db, run.id, EventType.SPEC_SAVED, {"version": workspace.spec_version})
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": f"Spec saved (v{workspace.spec_version})", "level": "info"})
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 50})
        
        # ====================================================================
        # Build Phase (Optional - can be triggered separately)
        # ====================================================================
        
        # For now, we'll just mark as succeeded without building
        # The user can trigger a build separately via POST /api/runs/workspace/{id}/build
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Generation complete. Use 'Build' to compile to JAR.", "level": "info"})
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 100})
        
        # Create assistant message
        if run.conversation_id:
            assistant_message = Message(
                conversation_id=run.conversation_id,
                role="assistant",
                content=_generate_assistant_response(new_spec, spec_delta),
                content_type="markdown",
                trigger_run_id=run.id
            )
            db.add(assistant_message)
        
        # Mark run as succeeded
        run.status = "succeeded"
        run.finished_at = datetime.utcnow()
        run.result = {
            "spec_version": workspace.spec_version,
            "items_added": len(spec_delta.get("items_to_add", [])),
            "blocks_added": len(spec_delta.get("blocks_to_add", [])),
            "tools_added": len(spec_delta.get("tools_to_add", []))
        }
        
        db.commit()
        
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {"status": "succeeded"})
        
    except Exception as e:
        print(f"[RunService] Error executing run {run_id}: {e}")
        traceback.print_exc()
        _fail_run(db, run, str(e))
    finally:
        db.close()


def execute_build(run_id: str):
    """
    Execute a build run in background
    
    Compiles the current workspace spec to a JAR file using the V2 pipeline.
    """
    db = SessionLocal()
    
    try:
        run_uuid = UUID(run_id)
        run = db.query(Run).filter(Run.id == run_uuid).first()
        
        if not run:
            print(f"[RunService] Run {run_id} not found")
            return
        
        workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
        if not workspace:
            _fail_run(db, run, "Workspace not found")
            return
        
        if not workspace.spec:
            _fail_run(db, run, "No spec to build")
            return
        
        # Update run status
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()
        
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {"status": "running"})
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Starting build...", "level": "info"})
        
        # ====================================================================
        # Build using V2 Pipeline
        # ====================================================================
        
        try:
            from agents.pipeline import ModGenerationPipeline
            from agents.schemas import ModSpec
            
            # Create pipeline
            job_id = str(run.id)
            pipeline = ModGenerationPipeline(job_id=job_id)
            
            # Progress callback
            def progress_callback(msg: str):
                emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": msg, "level": "info"})
                
                # Update progress based on message content
                progress = _estimate_progress_from_log(msg)
                if progress:
                    emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": progress})
            
            # Convert workspace spec to ModSpec
            spec_data = workspace.spec
            mod_spec = ModSpec(**spec_data)
            
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": f"Building mod: {mod_spec.mod_name}", "level": "info"})
            emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "compile"})
            
            # Initialize spec in pipeline
            pipeline.spec_manager.initialize_spec(mod_spec)
            
            # Run the build phases (skip orchestrator since we already have a spec)
            # Phase 1: Compiler - Spec → IR
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Phase 1: Compiling spec to IR...", "level": "info"})
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 20})
            
            mod_ir = pipeline.compiler.compile(mod_spec)
            
            # Phase 2: Planner - IR → Task DAG
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Phase 2: Planning tasks...", "level": "info"})
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 30})
            
            task_dag = pipeline.planner.plan(mod_ir, workspace_root=pipeline.workspace_dir)
            
            # Phase 3: Executor - Run tasks
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Phase 3: Executing tasks...", "level": "info"})
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 40})
            
            from agents.tools.tool_registry import create_tool_registry
            tool_registry = create_tool_registry(pipeline.workspace_dir)
            
            from agents.core.executor import Executor
            executor = Executor(
                workspace_dir=pipeline.workspace_dir,
                tool_registry=tool_registry
            )
            
            exec_result = executor.execute(task_dag, progress_callback=progress_callback)
            
            emit_event_sync(db, run.id, EventType.TASK_FINISHED, {"task": "execute", "result": exec_result})
            
            # Phase 4: Validator
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Phase 4: Validating...", "level": "info"})
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 70})
            
            try:
                validation_result = pipeline.validator.validate(ir=mod_ir)
                emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": f"Validation passed ({validation_result.get('warnings', 0)} warnings)", "level": "info"})
            except Exception as ve:
                emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": f"Validation warning: {ve}", "level": "warning"})
            
            # Phase 5: Builder - Gradle build
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": "Phase 5: Building JAR (this may take 1-2 minutes)...", "level": "info"})
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 80})
            emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "gradle_build"})
            
            build_result = pipeline.builder.build(
                mod_id=mod_ir.mod_id,
                progress_callback=progress_callback
            )
            
            emit_event_sync(db, run.id, EventType.TASK_FINISHED, {"task": "gradle_build", "result": build_result})
            
            if build_result["status"] == "success":
                jar_path = build_result["jar_path"]
                
                # Copy JAR to downloads
                import shutil
                final_jar_path = DOWNLOADS_DIR / f"{mod_ir.mod_id}.jar"
                shutil.copy(jar_path, final_jar_path)
                
                # Create artifact record
                artifact = Artifact(
                    run_id=run.id,
                    workspace_id=workspace.id,
                    artifact_type="jar",
                    file_path=str(final_jar_path),
                    file_name=f"{mod_ir.mod_id}.jar",
                    file_size=final_jar_path.stat().st_size if final_jar_path.exists() else None,
                    mime_type="application/java-archive",
                    meta_data={
                        "mod_id": mod_ir.mod_id,
                        "mod_name": mod_ir.mod_name,
                        "version": mod_spec.version
                    }
                )
                db.add(artifact)
                db.commit()
                db.refresh(artifact)
                
                emit_event_sync(db, run.id, EventType.ARTIFACT_CREATED, {
                    "artifact_id": str(artifact.id),
                    "artifact_type": "jar",
                    "file_name": artifact.file_name,
                    "download_url": f"/api/runs/{run.id}/artifacts/{artifact.id}/download"
                })
                
                emit_event_sync(db, run.id, EventType.LOG_APPEND, {"message": f"Build successful: {artifact.file_name}", "level": "info"})
                emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 100})
                
                # Mark run as succeeded
                run.status = "succeeded"
                run.finished_at = datetime.utcnow()
                run.result = {
                    "mod_id": mod_ir.mod_id,
                    "mod_name": mod_ir.mod_name,
                    "jar_file": artifact.file_name,
                    "artifact_id": str(artifact.id)
                }
                
                db.commit()
                emit_event_sync(db, run.id, EventType.RUN_STATUS, {"status": "succeeded"})
                
            else:
                error_msg = build_result.get("error", "Build failed")
                _fail_run(db, run, error_msg)
                
        except Exception as pe:
            print(f"[RunService] Pipeline error: {pe}")
            traceback.print_exc()
            _fail_run(db, run, f"Build failed: {str(pe)}")
        
    except Exception as e:
        print(f"[RunService] Error executing build {run_id}: {e}")
        traceback.print_exc()
        if run:
            _fail_run(db, run, str(e))
    finally:
        db.close()


def _fail_run(db, run: Run, error: str):
    """Mark a run as failed"""
    run.status = "failed"
    run.finished_at = datetime.utcnow()
    run.error = error
    db.commit()
    
    emit_event_sync(db, run.id, EventType.LOG_ERROR, {"message": error, "level": "error"})
    emit_event_sync(db, run.id, EventType.RUN_STATUS, {"status": "failed", "error": error})


def _estimate_progress_from_log(msg: str) -> Optional[int]:
    """Estimate progress from log message"""
    if "Phase 1" in msg or "Converting" in msg:
        return 10
    elif "Phase 2" in msg or "Applying" in msg:
        return 20
    elif "Phase 3" in msg or "Compiling" in msg:
        return 30
    elif "Phase 4" in msg or "Planning" in msg:
        return 40
    elif "Phase 5" in msg or "Executing" in msg:
        return 50
    elif "Phase 6" in msg or "Validating" in msg:
        return 70
    elif "Phase 7" in msg or "Building" in msg:
        return 80
    return None


# ============================================================================
# Placeholder Functions (Agent team will implement)
# ============================================================================

def _generate_spec_delta_placeholder(user_prompt: str) -> Dict[str, Any]:
    """
    Placeholder for AI spec delta generation
    
    TODO: Agent team will implement this using Orchestrator
    """
    # For now, generate a simple placeholder delta
    import re
    
    # Try to extract item name from prompt
    prompt_lower = user_prompt.lower()
    
    # Default item
    item_name = "Custom Item"
    item_id = "custom_item"
    
    # Try to extract meaningful name
    match = re.search(r'create\s+(?:a\s+)?([a-z\s]+)(?:\s+item)?', prompt_lower)
    if match:
        item_name = match.group(1).strip().title()
        item_id = item_name.lower().replace(' ', '_')
    
    return {
        "delta_type": "update",
        "mod_name": "Custom Mod",
        "mod_id": "custom_mod",
        "items_to_add": [
            {
                "item_name": item_name,
                "item_id": item_id,
                "description": f"A custom {item_name} generated by AI",
                "max_stack_size": 64,
                "rarity": "COMMON",
                "fireproof": False,
                "creative_tab": "MISC"
            }
        ],
        "blocks_to_add": [],
        "tools_to_add": []
    }


def _apply_spec_delta_placeholder(current_spec: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder for applying spec delta
    
    TODO: Use SpecManager for proper delta application
    """
    new_spec = current_spec.copy()
    
    # Update basic fields
    if delta.get("mod_name"):
        new_spec["mod_name"] = delta["mod_name"]
    if delta.get("mod_id"):
        new_spec["mod_id"] = delta["mod_id"]
    
    # Initialize lists if needed
    if "items" not in new_spec:
        new_spec["items"] = []
    if "blocks" not in new_spec:
        new_spec["blocks"] = []
    if "tools" not in new_spec:
        new_spec["tools"] = []
    
    # Add new items
    for item in delta.get("items_to_add", []):
        new_spec["items"].append(item)
    
    # Add new blocks
    for block in delta.get("blocks_to_add", []):
        new_spec["blocks"].append(block)
    
    # Add new tools
    for tool in delta.get("tools_to_add", []):
        new_spec["tools"].append(tool)
    
    # Set version if not set
    if "version" not in new_spec:
        new_spec["version"] = "1.0.0"
    
    return new_spec


def _generate_assistant_response(spec: Dict[str, Any], delta: Dict[str, Any]) -> str:
    """Generate assistant response message"""
    items_added = len(delta.get("items_to_add", []))
    blocks_added = len(delta.get("blocks_to_add", []))
    tools_added = len(delta.get("tools_to_add", []))
    
    parts = []
    
    if items_added > 0:
        items = delta.get("items_to_add", [])
        item_names = ", ".join([i.get("item_name", "Unknown") for i in items])
        parts.append(f"**Items added:** {item_names}")
    
    if blocks_added > 0:
        blocks = delta.get("blocks_to_add", [])
        block_names = ", ".join([b.get("block_name", "Unknown") for b in blocks])
        parts.append(f"**Blocks added:** {block_names}")
    
    if tools_added > 0:
        tools = delta.get("tools_to_add", [])
        tool_names = ", ".join([t.get("tool_name", "Unknown") for t in tools])
        parts.append(f"**Tools added:** {tool_names}")
    
    if not parts:
        return "I've updated the mod specification. Click **Build** to compile your mod."
    
    return "I've updated the mod specification:\n\n" + "\n".join(parts) + "\n\nClick **Build** when you're ready to compile your mod."

