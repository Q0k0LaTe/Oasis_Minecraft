"""
Run Service - Background task execution for runs

Handles:
- Generation runs (user message → Orchestrator → SpecManager → DB)
- Build runs (compile current spec to JAR)
- Event emission during execution

Architecture:
- Phase 1-2 are INTERACTIVE: Orchestrator generates deltas, SpecManager applies them
- Phase 1-2 can loop (human-in-the-loop) until user triggers Build
- Phase 3+ (Build) runs the full pipeline: Compiler → Planner → Executor → Validator → Builder

WORKFLOW STATE MACHINE:
=======================
[queued] → execute_run() → [running] → Orchestrator → [awaiting_approval]
                                                              ↓
                                                    User calls approve → [running] → SpecManager → [succeeded]
                                                              ↓
                                                    User calls reject  → [rejected]

KEY STATES:
- awaiting_approval: Run is paused waiting for user to review AI-generated deltas
  * Enter condition: Orchestrator returns deltas (even 0 deltas)
  * Continue via: POST /api/runs/{run_id}/approve
  * Cancel via: POST /api/runs/{run_id}/reject
"""
import traceback
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session as DBSession

from database import SessionLocal, Run, Workspace, Message, Artifact, SpecHistory, Conversation
from services.event_service import (
    emit_event_sync,
    EventType,
)
import base64
from config import GENERATED_DIR, DOWNLOADS_DIR

# Import agents
from agents.core.orchestrator import Orchestrator, OrchestratorResponse, ConversationContext
from agents.core.spec_manager import SpecManager
from agents.schemas import ModSpec, SpecDelta

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================================
# Run Execution Entry Points
# ============================================================================

def execute_run(run_id: str):
    """
    Execute a generation run in background (Phase 1-2 only)
    
    This is called from the conversations router when a user sends a message
    with trigger_run=True.
    
    Flow (Phase 1-2 - Interactive Spec Generation):
    1. Load run, workspace, and conversation context
    2. Phase 1: Call Orchestrator to generate SpecDeltas
    3. PAUSE at awaiting_approval - Wait for user to approve/reject
    4. Phase 2 (on approve): Apply deltas via SpecManager and persist to DB
    
    IMPORTANT: This function EXITS at awaiting_approval state.
    The workflow continues via approve_run_deltas() or reject_run_deltas().
    
    Note: This does NOT run the full pipeline (build). User triggers build separately.
    """
    logger.info(f"[execute_run] START run_id={run_id}")
    db = SessionLocal()
    
    try:
        run_uuid = UUID(run_id)
        run = db.query(Run).filter(Run.id == run_uuid).first()
        
        if not run:
            logger.error(f"[execute_run] Run {run_id} NOT FOUND")
            return
        
        logger.info(f"[execute_run] Run found: status={run.status}, workspace_id={run.workspace_id}")
        
        workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
        if not workspace:
            logger.error(f"[execute_run] Workspace not found for run {run_id}")
            _fail_run(db, run, "Workspace not found")
            return
        
        logger.info(f"[execute_run] Workspace: name={workspace.name}, spec_version={workspace.spec_version}")
        
        # Update run status to running
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()
        logger.info(f"[execute_run] Status changed: queued → running")
        
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {
            "status": "running",
            "workspace_id": str(workspace.id),
            "run_id": str(run.id)
        })
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "Starting generation run...",
            "level": "info"
        })
        
        # Get trigger message
        trigger_message = None
        if run.trigger_message_id:
            trigger_message = db.query(Message).filter(Message.id == run.trigger_message_id).first()
        
        user_prompt = trigger_message.content if trigger_message else "Generate a mod"
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": f"Processing: {user_prompt[:100]}{'...' if len(user_prompt) > 100 else ''}",
            "level": "info"
        })
        
        # Build conversation context from previous messages
        conversation_context = _build_conversation_context(db, run.conversation_id)
        
        # ====================================================================
        # Phase 1: Orchestrator - Convert prompt to SpecDeltas
        # ====================================================================
        logger.info(f"[execute_run] PHASE 1 START: Calling Orchestrator")
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "Phase 1: Analyzing prompt with AI...",
            "level": "info"
        })
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 10})
        emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "orchestrator"})
        
        # Load current spec from workspace (may be None for new workspace)
        current_spec = _load_spec_from_workspace(workspace)
        logger.info(f"[execute_run] Current spec: {'exists' if current_spec else 'None'}")
        
        # Call Orchestrator
        orchestrator = Orchestrator()
        logger.info(f"[execute_run] Calling orchestrator.process_prompt()")
        orchestrator_response = orchestrator.process_prompt(
            user_prompt=user_prompt,
            current_spec=current_spec,
            context=conversation_context
        )
        
        logger.info(f"[execute_run] PHASE 1 COMPLETE: deltas={len(orchestrator_response.deltas)}, requires_input={orchestrator_response.requires_user_input}")
        
        emit_event_sync(db, run.id, EventType.TASK_FINISHED, {
            "task": "orchestrator",
            "deltas_count": len(orchestrator_response.deltas),
            "requires_user_input": orchestrator_response.requires_user_input
        })
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": f"✓ Generated {len(orchestrator_response.deltas)} spec changes",
            "level": "info"
        })
        
        if orchestrator_response.clarifying_questions:
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"Questions: {', '.join(orchestrator_response.clarifying_questions)}",
                "level": "warning"
            })
        
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 30})
        
        # Preview the deltas (before applying)
        deltas_data = []
        for i, delta in enumerate(orchestrator_response.deltas):
            delta_dict = delta.model_dump(exclude_none=True)
            deltas_data.append(delta_dict)
            emit_event_sync(db, run.id, EventType.SPEC_PREVIEW, {
                "workspace_id": str(workspace.id),
                "run_id": str(run.id),
                "delta_index": i,
                "total_deltas": len(orchestrator_response.deltas),
                "delta": delta_dict
            })
        
        # ====================================================================
        # PAUSE: Wait for user approval before applying deltas
        # ====================================================================
        logger.info(f"[execute_run] ENTERING AWAITING_APPROVAL STATE")
        logger.info(f"[execute_run] Pending deltas count: {len(deltas_data)}")
        logger.info(f"[execute_run] >>> WORKFLOW PAUSED - Waiting for user to call:")
        logger.info(f"[execute_run] >>>   POST /api/runs/{run.id}/approve  (to apply changes)")
        logger.info(f"[execute_run] >>>   POST /api/runs/{run.id}/reject   (to discard changes)")
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": f"⏸ Generated {len(deltas_data)} changes. Waiting for your approval...",
            "level": "warning"
        })
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 40})
        
        # Store pending deltas in run.result
        run.status = "awaiting_approval"
        run.result = {
            "phase": "1",
            "spec_version": workspace.spec_version,
            "pending_deltas": deltas_data,
            "requires_user_input": orchestrator_response.requires_user_input,
            "clarifying_questions": orchestrator_response.clarifying_questions or [],
            "reasoning": orchestrator_response.reasoning,
            "user_prompt": user_prompt
        }
        db.commit()
        logger.info(f"[execute_run] Status committed: running → awaiting_approval")
        
        # Emit awaiting_approval event with all info frontend needs
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {
            "status": "awaiting_approval",
            "workspace_id": str(workspace.id),
            "run_id": str(run.id)
        })
        
        emit_event_sync(db, run.id, EventType.RUN_AWAITING_APPROVAL, {
            "workspace_id": str(workspace.id),
            "run_id": str(run.id),
            "pending_deltas": deltas_data,
            "deltas_count": len(deltas_data),
            "requires_user_input": orchestrator_response.requires_user_input,
            "clarifying_questions": orchestrator_response.clarifying_questions or [],
            "reasoning": orchestrator_response.reasoning,
            "spec_version": workspace.spec_version,
            "current_spec_summary": {
                "items_count": len(current_spec.items) if current_spec else 0,
                "blocks_count": len(current_spec.blocks) if current_spec else 0,
                "tools_count": len(current_spec.tools) if current_spec else 0,
            }
        })
        logger.info(f"[execute_run] Emitted run.awaiting_approval event")
        
        # Create assistant message showing the preview
        if run.conversation_id:
            preview_text = _format_deltas_preview(deltas_data)
            questions_text = ""
            if orchestrator_response.clarifying_questions:
                questions_text = "\n\n**I also have some questions:**\n" + "\n".join([f"• {q}" for q in orchestrator_response.clarifying_questions])
            
            assistant_message = Message(
                conversation_id=run.conversation_id,
                role="assistant",
                content=f"I've analyzed your request and prepared the following changes:\n\n{preview_text}{questions_text}\n\n**Please review and click 'Approve' to apply these changes, or 'Reject' to discard them.**",
                content_type="markdown",
                trigger_run_id=run.id,
                meta_data={"pending_approval": True, "deltas_count": len(deltas_data)}
            )
            db.add(assistant_message)
            db.commit()
        
        # Exit - wait for user to approve/reject
        return
        
        # Create assistant message with summary
        if run.conversation_id:
            assistant_content = _generate_assistant_response(new_spec, applied_deltas, orchestrator_response)
            assistant_message = Message(
                conversation_id=run.conversation_id,
                role="assistant",
                content=assistant_content,
                content_type="markdown",
                trigger_run_id=run.id
            )
            db.add(assistant_message)
        
        # Mark run as succeeded
        run.status = "succeeded"
        run.finished_at = datetime.utcnow()
        run.result = {
            "phase": "1-2",
            "spec_version": workspace.spec_version,
            "items_count": len(new_spec.items) if new_spec else 0,
            "blocks_count": len(new_spec.blocks) if new_spec else 0,
            "tools_count": len(new_spec.tools) if new_spec else 0,
            "reasoning": orchestrator_response.reasoning
        }
        
        db.commit()
        
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {
            "status": "succeeded",
            "workspace_id": str(workspace.id),
            "run_id": str(run.id),
            "spec_version": workspace.spec_version
        })
        
    except Exception as e:
        print(f"[RunService] Error executing run {run_id}: {e}")
        traceback.print_exc()
        _fail_run(db, run, str(e))
    finally:
        db.close()


def approve_run_deltas(
    run_id: str,
    modified_deltas: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Approve pending deltas and apply them to the workspace spec (Phase 2)
    
    Called when user clicks 'Approve' on the preview.
    Optionally accepts modified deltas if user edited them before approving.
    
    NOTE: Even if there are 0 deltas, approval should succeed (marks run as complete).
    
    Args:
        run_id: The run ID
        modified_deltas: Optional list of modified deltas to use instead of pending ones
        
    Returns:
        Dict with success status, new spec version, and spec summary
    """
    logger.info(f"[approve_run_deltas] START run_id={run_id}")
    db = SessionLocal()
    
    try:
        run_uuid = UUID(run_id)
        run = db.query(Run).filter(Run.id == run_uuid).first()
        
        if not run:
            logger.error(f"[approve_run_deltas] Run {run_id} NOT FOUND")
            return {"success": False, "error": "Run not found"}
        
        logger.info(f"[approve_run_deltas] Run found: status={run.status}")
        
        if run.status != "awaiting_approval":
            logger.error(f"[approve_run_deltas] Run not in awaiting_approval state: {run.status}")
            return {"success": False, "error": f"Run is not awaiting approval (status: {run.status})"}
        
        workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
        if not workspace:
            logger.error(f"[approve_run_deltas] Workspace not found")
            return {"success": False, "error": "Workspace not found"}
        
        # Get deltas to apply (modified ones or original pending ones)
        pending_result = run.result or {}
        deltas_data = modified_deltas if modified_deltas is not None else pending_result.get("pending_deltas", [])
        
        logger.info(f"[approve_run_deltas] Deltas to apply: {len(deltas_data)}")
        
        # NOTE: Even 0 deltas is valid - just means no changes to make
        # The approval still succeeds and marks the run as complete
        
        user_prompt = pending_result.get("user_prompt", "User request")
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "✓ Changes approved. Applying to spec...",
            "level": "info"
        })
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {
            "status": "running",
            "workspace_id": str(workspace.id),
            "run_id": str(run.id)
        })
        
        run.status = "running"
        db.commit()
        logger.info(f"[approve_run_deltas] Status changed: awaiting_approval → running")
        
        # ====================================================================
        # Phase 2: Apply deltas and persist to DB
        # ====================================================================
        logger.info(f"[approve_run_deltas] PHASE 2 START: Applying {len(deltas_data)} deltas")
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "Phase 2: Applying spec changes...",
            "level": "info"
        })
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 50})
        emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "spec_manager"})
        
        # Convert dicts back to SpecDelta objects
        deltas = [SpecDelta(**d) for d in deltas_data]
        
        # Apply deltas and get new spec (even if empty, this handles spec initialization)
        new_spec, applied_deltas = _apply_deltas_to_workspace(
            db=db,
            workspace=workspace,
            deltas=deltas,
            run=run,
            change_source="ai",
            change_notes=f"Generated from: {user_prompt[:50]}..."
        )
        
        logger.info(f"[approve_run_deltas] PHASE 2 COMPLETE: applied {len(applied_deltas)} deltas")
        emit_event_sync(db, run.id, EventType.TASK_FINISHED, {"task": "spec_manager"})
        
        # Emit spec.saved event with full details
        emit_event_sync(db, run.id, EventType.SPEC_SAVED, {
            "workspace_id": str(workspace.id),
            "run_id": str(run.id),
            "spec_version": workspace.spec_version,
            "spec": new_spec.model_dump() if new_spec else None,
            "items_count": len(new_spec.items) if new_spec else 0,
            "blocks_count": len(new_spec.blocks) if new_spec else 0,
            "tools_count": len(new_spec.tools) if new_spec else 0
        })
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": f"✓ Spec saved (v{workspace.spec_version})",
            "level": "info"
        })
        
        if new_spec:
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"  - Mod: {new_spec.mod_name} | Items: {len(new_spec.items)}, Blocks: {len(new_spec.blocks)}, Tools: {len(new_spec.tools)}",
                "level": "info"
            })
        
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 90})
        
        # ====================================================================
        # Check if there are clarifying questions (continue Phase 1-2 loop)
        # ====================================================================
        
        requires_input = pending_result.get("requires_user_input", False)
        clarifying_questions = pending_result.get("clarifying_questions", [])
        
        if requires_input and clarifying_questions:
            run.status = "awaiting_input"
            run.result = {
                "phase": "1-2",
                "spec_version": workspace.spec_version,
                "requires_user_input": True,
                "clarifying_questions": clarifying_questions,
                "reasoning": pending_result.get("reasoning", "")
            }
            db.commit()
            
            emit_event_sync(db, run.id, EventType.RUN_STATUS, {
                "status": "awaiting_input",
                "workspace_id": str(workspace.id),
                "run_id": str(run.id)
            })
            
            emit_event_sync(db, run.id, EventType.RUN_AWAITING_INPUT, {
                "workspace_id": str(workspace.id),
                "run_id": str(run.id),
                "requires_user_input": True,
                "clarifying_questions": clarifying_questions,
                "spec_version": workspace.spec_version
            })
            
            # Create assistant message asking for clarification
            if run.conversation_id:
                questions_text = "\n".join([f"• {q}" for q in clarifying_questions])
                assistant_message = Message(
                    conversation_id=run.conversation_id,
                    role="assistant",
                    content=f"Changes applied successfully! I have a few follow-up questions:\n\n{questions_text}\n\nPlease respond with your preferences.",
                    content_type="markdown",
                    trigger_run_id=run.id
                )
                db.add(assistant_message)
                db.commit()
            
            return {
                "success": True,
                "spec_version": workspace.spec_version,
                "status": "awaiting_input",
                "clarifying_questions": clarifying_questions
            }
        
        # ====================================================================
        # Phase 1-2 Complete - Ready for Build
        # ====================================================================
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "✓ Generation complete. Click 'Build' to compile your mod to JAR.",
            "level": "info"
        })
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 100})
        
        # Create assistant message with summary
        if run.conversation_id:
            assistant_message = Message(
                conversation_id=run.conversation_id,
                role="assistant",
                content=_generate_assistant_response(new_spec, applied_deltas),
                content_type="markdown",
                trigger_run_id=run.id
            )
            db.add(assistant_message)
        
        # Mark run as succeeded
        run.status = "succeeded"
        run.finished_at = datetime.utcnow()
        run.progress = 100
        run.result = {
            "phase": "1-2",
            "spec_version": workspace.spec_version,
            "deltas_applied": len(applied_deltas),
            "items_count": len(new_spec.items) if new_spec else 0,
            "blocks_count": len(new_spec.blocks) if new_spec else 0,
            "tools_count": len(new_spec.tools) if new_spec else 0
        }
        db.commit()
        
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {
            "status": "succeeded",
            "workspace_id": str(workspace.id),
            "run_id": str(run.id)
        })
        
        return {
            "success": True,
            "spec_version": workspace.spec_version,
            "status": "succeeded",
            "spec_summary": {
                "mod_name": new_spec.mod_name if new_spec else None,
                "items_count": len(new_spec.items) if new_spec else 0,
                "blocks_count": len(new_spec.blocks) if new_spec else 0,
                "tools_count": len(new_spec.tools) if new_spec else 0
            }
        }
        
    except Exception as e:
        print(f"[RunService] Error approving run {run_id}: {e}")
        traceback.print_exc()
        if run:
            _fail_run(db, run, str(e))
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def reject_run_deltas(run_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Reject pending deltas - do not apply them to the workspace spec
    
    Called when user clicks 'Reject' on the preview.
    The run is marked as rejected and no changes are made to the spec.
    
    Args:
        run_id: The run ID
        reason: Optional reason for rejection
        
    Returns:
        Dict with success status
    """
    logger.info(f"[reject_run_deltas] START run_id={run_id}, reason={reason}")
    db = SessionLocal()
    
    try:
        run_uuid = UUID(run_id)
        run = db.query(Run).filter(Run.id == run_uuid).first()
        
        if not run:
            logger.error(f"[reject_run_deltas] Run {run_id} NOT FOUND")
            return {"success": False, "error": "Run not found"}
        
        logger.info(f"[reject_run_deltas] Run found: status={run.status}")
        
        if run.status != "awaiting_approval":
            logger.error(f"[reject_run_deltas] Run not in awaiting_approval state: {run.status}")
            return {"success": False, "error": f"Run is not awaiting approval (status: {run.status})"}
        
        workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
        
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": f"✗ Changes rejected{': ' + reason if reason else ''}",
            "level": "warning"
        })
        
        # Mark run as rejected (using canceled status)
        run.status = "rejected"
        run.finished_at = datetime.utcnow()
        run.error = reason or "User rejected changes"
        run.result = {
            "phase": "1",
            "rejected": True,
            "rejection_reason": reason,
            "pending_deltas_discarded": len((run.result or {}).get("pending_deltas", []))
        }
        db.commit()
        logger.info(f"[reject_run_deltas] Status changed: awaiting_approval → rejected")
        
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {
            "status": "rejected",
            "workspace_id": str(workspace.id) if workspace else None,
            "run_id": str(run.id),
            "reason": reason
        })
        logger.info(f"[reject_run_deltas] COMPLETE")
        
        # Create assistant message acknowledging rejection
        if run.conversation_id:
            assistant_message = Message(
                conversation_id=run.conversation_id,
                role="assistant",
                content=f"Changes discarded{': ' + reason if reason else ''}. No modifications were made to your mod spec. Feel free to send a new message with different instructions.",
                content_type="text",
                trigger_run_id=run.id
            )
            db.add(assistant_message)
            db.commit()
        
        return {
            "success": True,
            "status": "rejected",
            "message": "Changes rejected and discarded"
        }

    except Exception as e:
        print(f"[RunService] Error rejecting run {run_id}: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def select_texture_variant(
    run_id: str,
    entity_id: str,
    selected_variant_index: int
) -> Dict[str, Any]:
    """
    Select a texture variant for an entity during build

    Called when user clicks on one of the texture variants to select it.
    Stores the selection and checks if all textures have been selected.
    If all selections are made, continues the build.

    Args:
        run_id: The run ID
        entity_id: ID of the entity (item/block/tool) the texture is for
        selected_variant_index: Index of the selected variant (0-based)

    Returns:
        Dict with success status and remaining selections count
    """
    logger.info(f"[select_texture_variant] START run_id={run_id}, entity_id={entity_id}, index={selected_variant_index}")
    db = SessionLocal()

    try:
        run_uuid = UUID(run_id)
        # Use with_for_update() to lock the row and prevent race conditions
        # when multiple texture selections come in simultaneously
        run = db.query(Run).filter(Run.id == run_uuid).with_for_update().first()

        if not run:
            logger.error(f"[select_texture_variant] Run {run_id} NOT FOUND")
            return {"success": False, "error": "Run not found"}

        # Refresh to ensure we have the latest data after acquiring lock
        db.refresh(run)

        logger.info(f"[select_texture_variant] Run found: status={run.status}")

        if run.status != "awaiting_texture_selection":
            logger.error(f"[select_texture_variant] Run not in awaiting_texture_selection state: {run.status}")
            return {"success": False, "error": f"Run is not awaiting texture selection (status: {run.status})"}

        workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
        if not workspace:
            logger.error(f"[select_texture_variant] Workspace not found")
            return {"success": False, "error": "Workspace not found"}

        # Get pending texture selections from run result
        # Make deep copies to avoid reference issues with JSON column
        import copy
        pending_result = copy.deepcopy(run.result) or {}
        pending_textures = pending_result.get("pending_textures", {})
        selected_textures = pending_result.get("selected_textures", {})

        logger.info(f"[select_texture_variant] Before selection - pending: {list(pending_textures.keys())}, selected: {list(selected_textures.keys())}")

        if entity_id not in pending_textures:
            return {"success": False, "error": f"Entity {entity_id} not found in pending textures"}

        entity_data = pending_textures[entity_id]
        variants = entity_data.get("variants", [])

        if selected_variant_index < 0 or selected_variant_index >= len(variants):
            return {"success": False, "error": f"Invalid variant index: {selected_variant_index}"}

        # Store the selection
        selected_textures[entity_id] = {
            "variant_index": selected_variant_index,
            "texture_data": variants[selected_variant_index],  # Base64 encoded
            "entity_type": entity_data.get("entity_type"),
            "name": entity_data.get("name")
        }

        # Remove from pending
        del pending_textures[entity_id]

        # Update run result
        run.result = {
            **pending_result,
            "pending_textures": pending_textures,
            "selected_textures": selected_textures
        }
        db.commit()

        emit_event_sync(db, run.id, EventType.TEXTURE_SELECTED, {
            "entity_id": entity_id,
            "selected_variant_index": selected_variant_index,
            "entity_name": entity_data.get("name"),
            "remaining_count": len(pending_textures)
        })

        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": f"✓ Selected texture variant {selected_variant_index + 1} for {entity_data.get('name', entity_id)}",
            "level": "info"
        })

        remaining_count = len(pending_textures)
        logger.info(f"[select_texture_variant] Selection saved. Remaining: {remaining_count}")

        # If all textures selected, continue the build
        if remaining_count == 0:
            logger.info(f"[select_texture_variant] All textures selected, continuing build...")
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": "✓ All textures selected. Continuing build...",
                "level": "info"
            })

            # Continue build in background
            from threading import Thread
            thread = Thread(target=continue_build_after_texture_selection, args=(run_id,))
            thread.start()

        return {
            "success": True,
            "message": f"Texture selected for {entity_data.get('name', entity_id)}",
            "remaining_selections": remaining_count
        }

    except Exception as e:
        print(f"[RunService] Error selecting texture for run {run_id}: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def continue_build_after_texture_selection(run_id: str):
    """
    Continue the build process after all textures have been selected

    This function resumes the build from Phase 6 (Validator) after
    texture selection is complete.
    """
    logger.info(f"[continue_build_after_texture_selection] START run_id={run_id}")
    db = SessionLocal()

    try:
        run_uuid = UUID(run_id)
        run = db.query(Run).filter(Run.id == run_uuid).first()

        if not run:
            logger.error(f"[continue_build_after_texture_selection] Run {run_id} NOT FOUND")
            return

        workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
        if not workspace:
            _fail_run(db, run, "Workspace not found")
            return

        # Update run status
        run.status = "running"
        db.commit()

        emit_event_sync(db, run.id, EventType.RUN_STATUS, {
            "status": "running",
            "workspace_id": str(workspace.id),
            "run_id": str(run.id)
        })

        # Get selected textures from run result
        pending_result = run.result or {}
        selected_textures = pending_result.get("selected_textures", {})
        mod_ir_data = pending_result.get("mod_ir")
        pipeline_job_id = pending_result.get("pipeline_job_id")

        if not mod_ir_data:
            _fail_run(db, run, "No mod IR found in run result")
            return

        # Reconstruct pipeline and apply selected textures
        from agents.pipeline import ModGenerationPipeline
        from agents.schemas import ModSpec

        # Create pipeline
        pipeline = ModGenerationPipeline(job_id=pipeline_job_id or str(run.id))

        # Get the mod spec
        spec_data = workspace.spec
        mod_spec = ModSpec(**spec_data)

        # Write selected textures to the mod assets
        from pathlib import Path
        assets_base = pipeline.workspace_dir / "src" / "main" / "resources" / "assets" / mod_ir_data.get("mod_id", "tutorialmod") / "textures"

        for entity_id, selection in selected_textures.items():
            entity_type = selection.get("entity_type", "item")
            texture_data = selection.get("texture_data")

            if texture_data:
                # Strip namespace prefix (e.g., "mymod:ruby" -> "ruby")
                texture_name = entity_id.split(":")[-1] if ":" in entity_id else entity_id

                # Determine texture path based on entity type
                if entity_type == "block":
                    texture_path = assets_base / "block" / f"{texture_name}.png"
                else:
                    texture_path = assets_base / "item" / f"{texture_name}.png"

                texture_path.parent.mkdir(parents=True, exist_ok=True)

                # Decode base64 and write texture
                if isinstance(texture_data, str):
                    texture_bytes = base64.b64decode(texture_data)
                else:
                    texture_bytes = texture_data

                texture_path.write_bytes(texture_bytes)
                logger.info(f"[continue_build] Wrote texture for {entity_id} to {texture_path}")

        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "✓ Applied selected textures to mod",
            "level": "info"
        })

        # Continue with Phase 6: Validator and Phase 7: Builder
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "Phase 6: Validating generated files...",
            "level": "info"
        })
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 70})

        # Reconstruct ModIR from stored data
        from agents.schemas import ModIR
        mod_ir = ModIR(**mod_ir_data)

        try:
            validation_result = pipeline.validator.validate(ir=mod_ir)
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"✓ Validation passed ({validation_result.get('warnings', 0)} warnings)",
                "level": "info"
            })
        except Exception as ve:
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"⚠ Validation warning: {ve}",
                "level": "warning"
            })

        # Phase 7: Builder - Gradle build
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "Phase 7: Building JAR with Gradle (1-2 minutes)...",
            "level": "info"
        })
        emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 80})
        emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "gradle_build"})

        def progress_callback(msg: str):
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": msg,
                "level": "info"
            })

        build_result = pipeline.builder.build(
            mod_id=mod_ir.mod_id,
            progress_callback=progress_callback
        )

        emit_event_sync(db, run.id, EventType.TASK_FINISHED, {
            "task": "gradle_build",
            "status": build_result.get("status")
        })

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
                    "version": mod_spec.version,
                    "spec_version": workspace.spec_version
                }
            )
            db.add(artifact)
            db.commit()
            db.refresh(artifact)

            emit_event_sync(db, run.id, EventType.ARTIFACT_CREATED, {
                "artifact_id": str(artifact.id),
                "artifact_type": "jar",
                "file_name": artifact.file_name,
                "download_url": f"/api/runs/{run.id}/artifacts/{artifact.id}/download",
                "workspace_id": str(workspace.id),
                "run_id": str(run.id)
            })

            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"✓ Build successful: {artifact.file_name}",
                "level": "info"
            })
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 100})

            # Mark run as succeeded
            run.status = "succeeded"
            run.finished_at = datetime.utcnow()
            run.result = {
                "phase": "build",
                "mod_id": mod_ir.mod_id,
                "mod_name": mod_ir.mod_name,
                "jar_file": artifact.file_name,
                "artifact_id": str(artifact.id),
                "spec_version": workspace.spec_version
            }

            db.commit()
            emit_event_sync(db, run.id, EventType.RUN_STATUS, {
                "status": "succeeded",
                "workspace_id": str(workspace.id),
                "run_id": str(run.id)
            })

        else:
            error_msg = build_result.get("error", "Build failed")
            _fail_run(db, run, error_msg)

    except Exception as e:
        print(f"[RunService] Error continuing build {run_id}: {e}")
        traceback.print_exc()
        if run:
            _fail_run(db, run, str(e))
    finally:
        db.close()


def execute_build(run_id: str):
    """
    Execute a build run in background (Phase 3+)
    
    Compiles the current workspace spec to a JAR file using the full pipeline:
    Phase 3: Compiler (Spec → IR)
    Phase 4: Planner (IR → Task DAG)
    Phase 5: Executor (Run tasks)
    Phase 6: Validator
    Phase 7: Builder (Gradle)
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
            _fail_run(db, run, "No spec to build. Generate a spec first.")
            return
        
        # Update run status
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()
        
        emit_event_sync(db, run.id, EventType.RUN_STATUS, {
            "status": "running",
            "workspace_id": str(workspace.id),
            "run_id": str(run.id)
        })
        emit_event_sync(db, run.id, EventType.LOG_APPEND, {
            "message": "Starting build...",
            "level": "info"
        })
        
        # ====================================================================
        # Build using V2 Pipeline (Phase 3-7)
        # ====================================================================
        
        try:
            from agents.pipeline import ModGenerationPipeline
            from agents.schemas import ModSpec
            
            # Create pipeline
            job_id = str(run.id)
            pipeline = ModGenerationPipeline(job_id=job_id)
            
            # Progress callback
            def progress_callback(msg: str):
                emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                    "message": msg,
                    "level": "info"
                })
                progress = _estimate_build_progress(msg)
                if progress:
                    emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": progress})
            
            # Convert workspace spec to ModSpec
            spec_data = workspace.spec
            mod_spec = ModSpec(**spec_data)
            
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"Building mod: {mod_spec.mod_name} (spec v{workspace.spec_version})",
                "level": "info"
            })
            
            # Initialize spec in pipeline
            pipeline.spec_manager.initialize_spec(mod_spec)
            
            # Phase 3: Compiler - Spec → IR
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": "Phase 3: Compiling spec to IR...",
                "level": "info"
            })
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 20})
            emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "compiler"})
            
            mod_ir = pipeline.compiler.compile(mod_spec)
            
            emit_event_sync(db, run.id, EventType.TASK_FINISHED, {"task": "compiler"})
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"✓ IR generated: {len(mod_ir.items)} items, {len(mod_ir.blocks)} blocks, {len(mod_ir.tools)} tools",
                "level": "info"
            })
            
            # Phase 4: Planner - IR → Task DAG
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": "Phase 4: Planning execution tasks...",
                "level": "info"
            })
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 30})
            emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "planner"})
            
            task_dag = pipeline.planner.plan(mod_ir, workspace_root=pipeline.workspace_dir)
            
            emit_event_sync(db, run.id, EventType.TASK_FINISHED, {"task": "planner"})
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"✓ Task plan: {task_dag.total_tasks} tasks",
                "level": "info"
            })
            
            # Phase 5: Executor - Run tasks
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": "Phase 5: Executing tasks...",
                "level": "info"
            })
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 40})
            emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "executor"})
            
            from agents.tools.tool_registry import create_tool_registry
            from agents.core.executor import Executor
            
            tool_registry = create_tool_registry(pipeline.workspace_dir)
            executor = Executor(
                workspace_dir=pipeline.workspace_dir,
                tool_registry=tool_registry
            )
            
            exec_result = executor.execute(task_dag, progress_callback=progress_callback)
            
            emit_event_sync(db, run.id, EventType.TASK_FINISHED, {
                "task": "executor",
                "completed": exec_result.get("completed_tasks", 0),
                "total": exec_result.get("total_tasks", 0)
            })

            # ====================================================================
            # Phase 5.5: Texture Selection (if textures were generated)
            # ====================================================================
            texture_results = exec_result.get("texture_results", {})

            if texture_results:
                logger.info(f"[execute_build] Texture generation complete. {len(texture_results)} entities need texture selection.")

                # Convert texture bytes to base64 for frontend
                pending_textures = {}
                for entity_id, texture_data in texture_results.items():
                    variants = texture_data.get("variants", [])
                    # Convert bytes to base64
                    variants_b64 = []
                    for variant in variants:
                        if isinstance(variant, bytes):
                            variants_b64.append(base64.b64encode(variant).decode('utf-8'))
                        else:
                            variants_b64.append(variant)

                    pending_textures[entity_id] = {
                        "variants": variants_b64,
                        "entity_type": texture_data.get("entity_type"),
                        "name": texture_data.get("name"),
                        "description": texture_data.get("description", "")
                    }

                emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                    "message": f"⏸ Generated {len(pending_textures)} textures. Please select your preferred variant for each.",
                    "level": "warning"
                })
                emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 55})

                # Store pending textures and mod_ir in run result
                run.status = "awaiting_texture_selection"
                run.result = {
                    "phase": "5.5",
                    "pending_textures": pending_textures,
                    "selected_textures": {},
                    "mod_ir": mod_ir.model_dump(),
                    "pipeline_job_id": job_id,
                    "spec_version": workspace.spec_version
                }
                db.commit()
                logger.info(f"[execute_build] Status changed: running → awaiting_texture_selection")

                emit_event_sync(db, run.id, EventType.RUN_STATUS, {
                    "status": "awaiting_texture_selection",
                    "workspace_id": str(workspace.id),
                    "run_id": str(run.id)
                })

                # Emit texture selection event with all texture variants
                emit_event_sync(db, run.id, EventType.TEXTURE_SELECTION_REQUIRED, {
                    "workspace_id": str(workspace.id),
                    "run_id": str(run.id),
                    "pending_textures": pending_textures,
                    "textures_count": len(pending_textures)
                })
                logger.info(f"[execute_build] Emitted texture.selection_required event")

                # Exit - wait for user to select textures
                return

            # Phase 6: Validator (no texture selection needed)
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": "Phase 6: Validating generated files...",
                "level": "info"
            })
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 70})
            
            try:
                validation_result = pipeline.validator.validate(ir=mod_ir)
                emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                    "message": f"✓ Validation passed ({validation_result.get('warnings', 0)} warnings)",
                    "level": "info"
                })
            except Exception as ve:
                emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                    "message": f"⚠ Validation warning: {ve}",
                    "level": "warning"
                })
            
            # Phase 7: Builder - Gradle build
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": "Phase 7: Building JAR with Gradle (1-2 minutes)...",
                "level": "info"
            })
            emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 80})
            emit_event_sync(db, run.id, EventType.TASK_STARTED, {"task": "gradle_build"})
            
            build_result = pipeline.builder.build(
                mod_id=mod_ir.mod_id,
                progress_callback=progress_callback
            )
            
            emit_event_sync(db, run.id, EventType.TASK_FINISHED, {
                "task": "gradle_build",
                "status": build_result.get("status")
            })
            
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
                        "version": mod_spec.version,
                        "spec_version": workspace.spec_version
                    }
                )
                db.add(artifact)
                db.commit()
                db.refresh(artifact)
                
                emit_event_sync(db, run.id, EventType.ARTIFACT_CREATED, {
                    "artifact_id": str(artifact.id),
                    "artifact_type": "jar",
                    "file_name": artifact.file_name,
                    "download_url": f"/api/runs/{run.id}/artifacts/{artifact.id}/download",
                    "workspace_id": str(workspace.id),
                    "run_id": str(run.id)
                })
                
                emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                    "message": f"✓ Build successful: {artifact.file_name}",
                    "level": "info"
                })
                emit_event_sync(db, run.id, EventType.RUN_PROGRESS, {"progress": 100})
                
                # Mark run as succeeded
                run.status = "succeeded"
                run.finished_at = datetime.utcnow()
                run.result = {
                    "phase": "build",
                    "mod_id": mod_ir.mod_id,
                    "mod_name": mod_ir.mod_name,
                    "jar_file": artifact.file_name,
                    "artifact_id": str(artifact.id),
                    "spec_version": workspace.spec_version
                }
                
                db.commit()
                emit_event_sync(db, run.id, EventType.RUN_STATUS, {
                    "status": "succeeded",
                    "workspace_id": str(workspace.id),
                    "run_id": str(run.id)
                })
                
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


# ============================================================================
# Helper Functions
# ============================================================================

def _build_conversation_context(db: DBSession, conversation_id: Optional[UUID]) -> ConversationContext:
    """
    Build conversation context from previous messages in the conversation.
    
    This provides the Orchestrator with context about what has been discussed.
    """
    context = ConversationContext()
    
    if not conversation_id:
        return context
    
    # Get recent messages from conversation (limit to last 10 for context)
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(
        Message.created_at.desc()
    ).limit(10).all()
    
    # Reverse to chronological order
    messages = list(reversed(messages))
    
    for msg in messages:
        if msg.role == "user" and msg.content:
            context.user_prompts.append(msg.content)
        elif msg.role == "assistant" and msg.content:
            # Extract any decisions from assistant messages
            if "added:" in msg.content.lower():
                context.decisions_made.append(msg.content[:100])
    
    return context


def _load_spec_from_workspace(workspace: Workspace) -> Optional[ModSpec]:
    """
    Load ModSpec from workspace.spec (JSONB column).
    
    Returns None if workspace has no spec.
    """
    if not workspace.spec:
        return None
    
    try:
        return ModSpec(**workspace.spec)
    except Exception as e:
        print(f"[RunService] Warning: Failed to parse workspace spec: {e}")
        return None


def _apply_deltas_to_workspace(
    db: DBSession,
    workspace: Workspace,
    deltas: List[SpecDelta],
    run: Run,
    change_source: str = "ai",
    change_notes: str = ""
) -> tuple[Optional[ModSpec], List[SpecDelta]]:
    """
    Apply spec deltas to workspace and persist to DB.
    
    This function:
    1. Creates a SpecManager (in-memory, no file system)
    2. Loads current spec from workspace
    3. Applies each delta
    4. Updates workspace.spec and workspace.spec_version
    5. Creates SpecHistory entry
    6. Emits spec.patch events for each delta
    
    Returns:
        Tuple of (new_spec, applied_deltas)
    """
    if not deltas:
        # No deltas to apply
        current_spec = _load_spec_from_workspace(workspace)
        return current_spec, []
    
    # Create temporary SpecManager (we'll handle DB persistence ourselves)
    temp_dir = GENERATED_DIR / f"temp_{run.id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    spec_manager = SpecManager(workspace_dir=temp_dir)
    
    # Load or initialize spec
    current_spec = _load_spec_from_workspace(workspace)
    if current_spec is None:
        # Initialize with empty spec
        current_spec = ModSpec(mod_name="New Mod")
    
    spec_manager.initialize_spec(current_spec)
    
    # Apply each delta
    applied_deltas = []
    for i, delta in enumerate(deltas):
        try:
            current_spec = spec_manager.apply_delta(delta)
            applied_deltas.append(delta)
            
            # Emit patch event
            emit_event_sync(db, run.id, EventType.SPEC_PATCH, {
                "workspace_id": str(workspace.id),
                "run_id": str(run.id),
                "delta_index": i,
                "operation": delta.operation,
                "path": delta.path,
                "success": True
            })
            
        except Exception as e:
            print(f"[RunService] Warning: Failed to apply delta {i}: {e}")
            emit_event_sync(db, run.id, EventType.LOG_APPEND, {
                "message": f"⚠ Failed to apply change {i}: {e}",
                "level": "warning"
            })
    
    # Persist to workspace
    if current_spec:
        # Update workspace.spec
        workspace.spec = current_spec.model_dump()
        workspace.spec_version += 1
        workspace.last_modified_at = datetime.utcnow()
        
        # Create SpecHistory entry
        history = SpecHistory(
            workspace_id=workspace.id,
            version=workspace.spec_version,
            spec=current_spec.model_dump(),
            delta={
                "deltas": [d.model_dump(exclude_none=True) for d in applied_deltas],
                "run_id": str(run.id)
            },
            change_source=change_source,
            change_notes=change_notes
        )
        db.add(history)
        db.commit()
    
    # Cleanup temp dir
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass
    
    return current_spec, applied_deltas


def _fail_run(db: DBSession, run: Run, error: str):
    """Mark a run as failed"""
    run.status = "failed"
    run.finished_at = datetime.utcnow()
    run.error = error
    db.commit()
    
    emit_event_sync(db, run.id, EventType.LOG_ERROR, {
        "message": error,
        "level": "error"
    })
    emit_event_sync(db, run.id, EventType.RUN_STATUS, {
        "status": "failed",
        "error": error,
        "workspace_id": str(run.workspace_id) if run.workspace_id else None,
        "run_id": str(run.id)
    })


def _estimate_build_progress(msg: str) -> Optional[int]:
    """Estimate progress from log message during build"""
    msg_lower = msg.lower()
    if "phase 3" in msg_lower or "compiling spec" in msg_lower:
        return 20
    elif "phase 4" in msg_lower or "planning" in msg_lower:
        return 30
    elif "phase 5" in msg_lower or "executing" in msg_lower:
        return 50
    elif "phase 6" in msg_lower or "validating" in msg_lower:
        return 70
    elif "phase 7" in msg_lower or "building" in msg_lower or "gradle" in msg_lower:
        return 85
    elif "build successful" in msg_lower:
        return 100
    return None


def _format_deltas_preview(deltas_data: List[Dict[str, Any]]) -> str:
    """
    Format deltas into a readable preview for the assistant message.
    
    Args:
        deltas_data: List of delta dictionaries
        
    Returns:
        Formatted markdown string showing the changes
    """
    if not deltas_data:
        return "*No changes*"
    
    lines = []
    
    # Group deltas by operation type
    adds = []
    updates = []
    removes = []
    
    for delta in deltas_data:
        op = delta.get("operation", "add")
        path = delta.get("path", "")
        value = delta.get("value", {})
        
        # Try to get a human-readable name
        name = (
            value.get("item_name") or 
            value.get("block_name") or 
            value.get("tool_name") or 
            value.get("mod_name") or
            value.get("name") or
            path
        )
        
        # Determine type from path
        item_type = "item"
        if "blocks" in path:
            item_type = "block"
        elif "tools" in path:
            item_type = "tool"
        elif "mod_" in path or path == "":
            item_type = "mod info"
        elif "items" in path:
            item_type = "item"
        
        if op == "add":
            adds.append(f"+ **{name}** ({item_type})")
        elif op == "update":
            updates.append(f"~ **{name}** ({item_type})")
        elif op == "remove":
            removes.append(f"- **{name}** ({item_type})")
    
    if adds:
        lines.append("**New:**")
        lines.extend(adds)
        lines.append("")
    
    if updates:
        lines.append("**Updated:**")
        lines.extend(updates)
        lines.append("")
    
    if removes:
        lines.append("**Removed:**")
        lines.extend(removes)
        lines.append("")
    
    return "\n".join(lines) if lines else "*No named changes*"


def _generate_assistant_response(
    spec: Optional[ModSpec],
    applied_deltas: List[SpecDelta],
    orchestrator_response: Optional[OrchestratorResponse] = None
) -> str:
    """
    Generate assistant response message summarizing what was created/changed.
    """
    if not spec:
        return "I've processed your request, but no spec was generated. Please try again with more details."
    
    parts = []
    
    # Count what was added
    items_added = sum(1 for d in applied_deltas if d.path and "items" in d.path and d.operation == "add")
    blocks_added = sum(1 for d in applied_deltas if d.path and "blocks" in d.path and d.operation == "add")
    tools_added = sum(1 for d in applied_deltas if d.path and "tools" in d.path and d.operation == "add")
    
    # Fallback: count from spec if deltas don't have path info
    if items_added == 0 and blocks_added == 0 and tools_added == 0:
        items_added = len(spec.items)
        blocks_added = len(spec.blocks)
        tools_added = len(spec.tools)
    
    # Build summary
    if items_added > 0:
        item_names = ", ".join([item.item_name for item in spec.items[-items_added:]])
        parts.append(f"**Items:** {item_names}")
    
    if blocks_added > 0:
        block_names = ", ".join([block.block_name for block in spec.blocks[-blocks_added:]])
        parts.append(f"**Blocks:** {block_names}")
    
    if tools_added > 0:
        tool_names = ", ".join([tool.tool_name for tool in spec.tools[-tools_added:]])
        parts.append(f"**Tools:** {tool_names}")
    
    if not parts:
        return f"I've updated the mod specification for **{spec.mod_name}**.\n\nClick **Build** when you're ready to compile your mod to a JAR file."
    
    content = f"I've updated **{spec.mod_name}** with the following:\n\n"
    content += "\n".join(parts)
    content += "\n\n---\n\n"
    content += "You can:\n"
    content += "- **Edit the spec** directly in the editor on the right\n"
    content += "- **Send another message** to add more items or make changes\n"
    content += "- **Click Build** when you're ready to compile your mod"
    
    return content


# ============================================================================
# Additional Entry Points for Spec Operations
# ============================================================================

def apply_spec_delta_from_api(
    workspace_id: str,
    deltas: List[Dict[str, Any]],
    change_source: str = "user",
    change_notes: str = ""
) -> Dict[str, Any]:
    """
    Apply spec deltas from API (user edits).
    
    This is called when user directly edits the spec or applies patches.
    It creates a new spec version without creating a Run.
    
    Returns:
        Dict with new spec_version and status
    """
    db = SessionLocal()
    
    try:
        workspace_uuid = UUID(workspace_id)
        workspace = db.query(Workspace).filter(Workspace.id == workspace_uuid).first()
        
        if not workspace:
            return {"success": False, "error": "Workspace not found"}
        
        # Convert dict deltas to SpecDelta objects
        spec_deltas = []
        for d in deltas:
            spec_deltas.append(SpecDelta(**d))
        
        # Create temporary spec manager
        temp_dir = GENERATED_DIR / f"temp_api_{workspace_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        spec_manager = SpecManager(workspace_dir=temp_dir)
        
        # Load current spec
        current_spec = _load_spec_from_workspace(workspace)
        if current_spec is None:
            current_spec = ModSpec(mod_name="New Mod")
        
        spec_manager.initialize_spec(current_spec)
        
        # Apply deltas
        for delta in spec_deltas:
            current_spec = spec_manager.apply_delta(delta)
        
        # Persist
        workspace.spec = current_spec.model_dump()
        workspace.spec_version += 1
        workspace.last_modified_at = datetime.utcnow()
        
        history = SpecHistory(
            workspace_id=workspace.id,
            version=workspace.spec_version,
            spec=current_spec.model_dump(),
            delta={"deltas": [d.model_dump(exclude_none=True) for d in spec_deltas]},
            change_source=change_source,
            change_notes=change_notes
        )
        db.add(history)
        db.commit()
        
        # Cleanup
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        
        return {
            "success": True,
            "spec_version": workspace.spec_version,
            "spec": current_spec.model_dump()
        }
        
    except Exception as e:
        print(f"[RunService] Error applying spec delta: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
