"""
Runs Router
FastAPI routes for run management and event streaming
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path

from database import get_db, Workspace, Run, RunEvent, Artifact, User, UserSession
from auth.dependencies import get_current_user
from schemas.run import (
    RunResponse,
    RunListResponse,
    RunEventResponse,
    ArtifactResponse,
    ArtifactListResponse,
)
from services.event_service import subscribe, get_events_since
from config import DOWNLOADS_DIR

router = APIRouter(prefix="/api/runs", tags=["runs"])


# ============================================================================
# Auth Helpers
# ============================================================================
# Using unified authentication dependency from auth.dependencies
# Supports both query parameter (backward compatible) and Authorization header


def get_run_or_404(run_id: UUID, user: User, db: Session) -> Run:
    """Get run by ID, ensuring user has access via workspace"""
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    # Check workspace access
    workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
    if not workspace or workspace.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return run


# ============================================================================
# Run Operations
# ============================================================================

@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a run by ID
    """
    run = get_run_or_404(run_id, user, db)
    
    return RunResponse.model_validate(run)


@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a running job
    
    Only works for runs in 'queued' or 'running' status.
    """
    run = get_run_or_404(run_id, user, db)
    
    if run.status not in ("queued", "running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel run with status '{run.status}'"
        )
    
    run.status = "canceled"
    run.finished_at = datetime.utcnow()
    
    # Emit cancellation event
    from services.event_service import emit_status_change
    emit_status_change(db, run.id, "canceled")
    
    db.commit()
    db.refresh(run)
    
    return RunResponse.model_validate(run)


# ============================================================================
# Delta Approval / Rejection
# ============================================================================

from pydantic import BaseModel
from typing import List, Dict, Any

class ApproveRequest(BaseModel):
    """Request body for approving run deltas"""
    modified_deltas: Optional[List[Dict[str, Any]]] = None
    """Optional: modified deltas to apply instead of the pending ones"""

class RejectRequest(BaseModel):
    """Request body for rejecting run deltas"""
    reason: Optional[str] = None
    """Optional: reason for rejection"""


class TextureSelectionRequest(BaseModel):
    """Request body for selecting a texture variant"""
    entity_id: str
    """ID of the entity (item/block/tool) the texture is for"""
    selected_variant_index: int
    """Index of the selected variant (0-based)"""


@router.post("/{run_id}/approve")
async def approve_run(
    run_id: UUID,
    request: Optional[ApproveRequest] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve pending spec deltas and apply them to the workspace
    
    Called when user reviews the AI-generated changes and clicks 'Approve'.
    Optionally accepts modified deltas if user edited them before approving.
    
    Only works for runs in 'awaiting_approval' status.
    
    Returns:
        - success: bool
        - spec_version: new version number
        - status: new run status ('succeeded' or 'awaiting_input' if questions remain)
        - spec_summary: summary of the updated spec
    """
    run = get_run_or_404(run_id, user, db)
    
    if run.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run is not awaiting approval (status: {run.status})"
        )
    
    # Call the service function
    from services.run_service import approve_run_deltas
    
    modified_deltas = request.modified_deltas if request else None
    result = approve_run_deltas(str(run_id), modified_deltas)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to approve deltas")
        )
    
    return result


@router.post("/{run_id}/reject")
async def reject_run(
    run_id: UUID,
    request: Optional[RejectRequest] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject pending spec deltas - discard them without applying
    
    Called when user reviews the AI-generated changes and clicks 'Reject'.
    The run is marked as rejected and no changes are made to the workspace spec.
    
    Only works for runs in 'awaiting_approval' status.
    
    Returns:
        - success: bool
        - status: 'rejected'
        - message: confirmation message
    """
    run = get_run_or_404(run_id, user, db)
    
    if run.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run is not awaiting approval (status: {run.status})"
        )
    
    # Call the service function
    from services.run_service import reject_run_deltas
    
    reason = request.reason if request else None
    result = reject_run_deltas(str(run_id), reason)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to reject deltas")
        )
    
    return result


@router.post("/{run_id}/select-texture")
async def select_texture(
    run_id: UUID,
    request: TextureSelectionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Select a texture variant for an entity during build

    Called when user selects one of the generated texture variants.
    The selected texture will be used for the entity in the final mod.

    Only works for runs in 'awaiting_texture_selection' status.

    Returns:
        - success: bool
        - message: confirmation message
        - remaining_selections: number of remaining texture selections needed
    """
    run = get_run_or_404(run_id, user, db)

    if run.status != "awaiting_texture_selection":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run is not awaiting texture selection (status: {run.status})"
        )

    # Call the service function
    from services.run_service import select_texture_variant

    result = select_texture_variant(
        str(run_id),
        request.entity_id,
        request.selected_variant_index
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to select texture")
        )

    return result


@router.get("/{run_id}/events")
async def stream_events(
    run_id: UUID,
    user: User = Depends(get_current_user),
    since: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Stream run events via Server-Sent Events (SSE)
    
    Connect to this endpoint to receive real-time updates about run progress.
    
    Query params:
    - since: Event ID to start from (for reconnection)
    
    Event types:
    - run.status: Status change (queued/running/succeeded/failed/canceled)
    - run.progress: Progress update (0-100)
    - log.append: Log message
    - spec.preview / spec.patch / spec.saved: Spec changes
    - asset.generated / asset.selected: Asset events
    - artifact.created: New artifact available
    - task.started / task.finished: Pipeline task events
    """
    run = get_run_or_404(run_id, user, db)
    
    # If there are missed events (since param), send them first
    if since:
        missed_events = get_events_since(db, run.id, since)
        # In a real implementation, you'd include these in the SSE stream
    
    return StreamingResponse(
        subscribe(str(run.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/{run_id}/events/history")
async def get_event_history(
    run_id: UUID,
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get historical events for a run (non-streaming)
    
    Useful for loading past events or catching up after reconnection.
    """
    run = get_run_or_404(run_id, user, db)
    
    # Get total count
    total = db.query(func.count(RunEvent.id)).filter(
        RunEvent.run_id == run.id
    ).scalar()
    
    # Get events
    events = db.query(RunEvent).filter(
        RunEvent.run_id == run.id
    ).order_by(
        RunEvent.created_at
    ).offset(skip).limit(limit).all()
    
    return {
        "events": [RunEventResponse.model_validate(e) for e in events],
        "total": total
    }


# ============================================================================
# Artifact Operations
# ============================================================================

@router.get("/{run_id}/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(
    run_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all artifacts produced by a run
    """
    run = get_run_or_404(run_id, user, db)
    
    artifacts = db.query(Artifact).filter(
        Artifact.run_id == run.id
    ).order_by(
        Artifact.created_at
    ).all()
    
    # Build responses with download URLs
    responses = []
    for artifact in artifacts:
        response = ArtifactResponse.model_validate(artifact)
        response.download_url = f"/api/runs/{run.id}/artifacts/{artifact.id}/download"
        responses.append(response)
    
    return ArtifactListResponse(
        artifacts=responses,
        total=len(responses)
    )


@router.get("/{run_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    run_id: UUID,
    artifact_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single artifact by ID
    """
    run = get_run_or_404(run_id, user, db)
    
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.run_id == run.id
    ).first()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )
    
    response = ArtifactResponse.model_validate(artifact)
    response.download_url = f"/api/runs/{run.id}/artifacts/{artifact.id}/download"
    
    return response


@router.get("/{run_id}/artifacts/{artifact_id}/download")
async def download_artifact(
    run_id: UUID,
    artifact_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download an artifact file
    """
    run = get_run_or_404(run_id, user, db)
    
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.run_id == run.id
    ).first()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )
    
    # Construct full path
    file_path = Path(artifact.file_path)
    if not file_path.is_absolute():
        file_path = DOWNLOADS_DIR / file_path
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact file not found"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=artifact.file_name,
        media_type=artifact.mime_type or "application/octet-stream"
    )


# ============================================================================
# Workspace Run Listing
# ============================================================================

@router.get("/workspace/{workspace_id}", response_model=RunListResponse)
async def list_workspace_runs(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all runs for a workspace
    
    Optional status filter: queued, running, succeeded, failed, canceled
    """
    
    # Check workspace access
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    if workspace.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Build query
    query = db.query(Run).filter(Run.workspace_id == workspace_id)
    
    if status_filter:
        query = query.filter(Run.status == status_filter)
    
    # Get total count
    total = query.count()
    
    # Get runs
    runs = query.order_by(
        Run.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return RunListResponse(
        runs=[RunResponse.model_validate(r) for r in runs],
        total=total
    )


# ============================================================================
# Build Trigger
# ============================================================================

@router.post("/workspace/{workspace_id}/build", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_build(
    workspace_id: UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a build run for a workspace
    
    This will compile the current spec to a JAR using the V2 pipeline.
    """
    
    # Check workspace access
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    if workspace.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if there's already a running build
    existing_run = db.query(Run).filter(
        Run.workspace_id == workspace_id,
        Run.run_type == "build",
        Run.status.in_(["queued", "running"])
    ).first()
    
    if existing_run:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A build is already in progress"
        )
    
    # Check if workspace has a spec
    if not workspace.spec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace has no spec to build"
        )
    
    # Create build run
    run = Run(
        workspace_id=workspace.id,
        run_type="build",
        status="queued"
    )
    db.add(run)
    
    # Update workspace timestamp
    workspace.last_modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(run)
    
    # Start build in background
    from services.run_service import execute_build
    background_tasks.add_task(execute_build, str(run.id))
    
    return RunResponse.model_validate(run)

