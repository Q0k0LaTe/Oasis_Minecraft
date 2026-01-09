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

async def get_current_user(
    session_token: str = None,
    db: Session = Depends(get_db)
) -> User:
    """Get current user from session token"""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    session = db.query(UserSession).filter(
        UserSession.session_token == session_token,
        UserSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled"
        )
    
    return user


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
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Get a run by ID
    """
    user = await get_current_user(session_token, db)
    run = get_run_or_404(run_id, user, db)
    
    return RunResponse.model_validate(run)


@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: UUID,
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Cancel a running job
    
    Only works for runs in 'queued' or 'running' status.
    """
    user = await get_current_user(session_token, db)
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


@router.get("/{run_id}/events")
async def stream_events(
    run_id: UUID,
    session_token: str,
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
    user = await get_current_user(session_token, db)
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
    session_token: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get historical events for a run (non-streaming)
    
    Useful for loading past events or catching up after reconnection.
    """
    user = await get_current_user(session_token, db)
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
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    List all artifacts produced by a run
    """
    user = await get_current_user(session_token, db)
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
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Get a single artifact by ID
    """
    user = await get_current_user(session_token, db)
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
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Download an artifact file
    """
    user = await get_current_user(session_token, db)
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
    session_token: str,
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all runs for a workspace
    
    Optional status filter: queued, running, succeeded, failed, canceled
    """
    user = await get_current_user(session_token, db)
    
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
    session_token: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger a build run for a workspace
    
    This will compile the current spec to a JAR using the V2 pipeline.
    """
    user = await get_current_user(session_token, db)
    
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

