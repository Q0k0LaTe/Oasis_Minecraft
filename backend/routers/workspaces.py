"""
Workspaces Router
FastAPI routes for workspace management and spec operations
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, Workspace, SpecHistory, User, UserSession
from auth.dependencies import get_current_user
from schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceListResponse,
    SpecUpdate,
    SpecPatch,
    SpecResponse,
    SpecHistoryResponse,
)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# ============================================================================
# Auth Helpers
# ============================================================================
# Using unified authentication dependency from auth.dependencies
# Supports both query parameter (backward compatible) and Authorization header


def get_workspace_or_404(
    workspace_id: UUID,
    user: User,
    db: Session
) -> Workspace:
    """Get workspace by ID, ensuring user has access"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check ownership (current version: only owner can access)
    if workspace.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return workspace


# ============================================================================
# Workspace CRUD
# ============================================================================

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new workspace
    
    Creates a new Minecraft Mod project workspace for the current user.
    Optionally initialize with a spec.
    """
    
    now = datetime.utcnow()
    workspace = Workspace(
        owner_id=user.id,
        name=request.name,
        description=request.description,
        cover_image_url=request.cover_image_url,
        spec=request.spec,
        spec_version=1 if request.spec else 0,
        last_modified_at=now
    )
    
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
    # Save initial spec to history if provided
    if request.spec:
        history = SpecHistory(
            workspace_id=workspace.id,
            version=1,
            spec=request.spec,
            change_source="user",
            change_notes="Initial spec"
        )
        db.add(history)
        db.commit()
    
    return WorkspaceResponse.model_validate(workspace)


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all workspaces for the current user
    
    Returns workspaces sorted by last_modified_at (most recent first).
    """
    
    # Get total count
    total = db.query(func.count(Workspace.id)).filter(
        Workspace.owner_id == user.id
    ).scalar()
    
    # Get workspaces
    workspaces = db.query(Workspace).filter(
        Workspace.owner_id == user.id
    ).order_by(
        Workspace.last_modified_at.desc()
    ).offset(skip).limit(limit).all()
    
    return WorkspaceListResponse(
        workspaces=[WorkspaceResponse.model_validate(w) for w in workspaces],
        total=total
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    include_spec: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get a single workspace by ID
    
    Set include_spec=false to exclude the spec from the response.
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    response = WorkspaceResponse.model_validate(workspace)
    if not include_spec:
        response.spec = None
    
    return response


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    request: WorkspaceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update workspace metadata (name, description, cover)
    
    Does not update spec - use the spec endpoints for that.
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Update fields
    if request.name is not None:
        workspace.name = request.name
    if request.description is not None:
        workspace.description = request.description
    if request.cover_image_url is not None:
        workspace.cover_image_url = request.cover_image_url
    
    workspace.last_modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(workspace)
    
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a workspace
    
    This will cascade delete all conversations, messages, runs, and assets.
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    db.delete(workspace)
    db.commit()
    
    return None


# ============================================================================
# Spec Operations
# ============================================================================

@router.get("/{workspace_id}/spec", response_model=SpecResponse)
async def get_spec(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current spec for a workspace
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    return SpecResponse(
        workspace_id=workspace.id,
        spec=workspace.spec or {},
        version=workspace.spec_version,
        last_modified_at=workspace.last_modified_at
    )


@router.put("/{workspace_id}/spec", response_model=SpecResponse)
async def update_spec(
    workspace_id: UUID,
    request: SpecUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Replace the entire spec (full update)
    
    This creates a new version in spec_history.
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Update spec
    workspace.spec = request.spec
    workspace.spec_version += 1
    workspace.last_modified_at = datetime.utcnow()
    
    # Save to history
    history = SpecHistory(
        workspace_id=workspace.id,
        version=workspace.spec_version,
        spec=request.spec,
        change_source="user",
        change_notes=request.change_notes
    )
    db.add(history)
    
    db.commit()
    db.refresh(workspace)
    
    return SpecResponse(
        workspace_id=workspace.id,
        spec=workspace.spec,
        version=workspace.spec_version,
        last_modified_at=workspace.last_modified_at
    )


@router.patch("/{workspace_id}/spec", response_model=SpecResponse)
async def patch_spec(
    workspace_id: UUID,
    request: SpecPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply partial updates to the spec (patch)
    
    Accepts a list of operations in the format:
    [{"op": "add"|"update"|"remove", "path": "items[0].rarity", "value": "RARE"}]
    
    This creates a new version in spec_history.
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Get current spec
    current_spec = workspace.spec or {}
    
    # Apply operations
    for op in request.operations:
        operation = op.get("op", op.get("operation"))
        path = op.get("path", "")
        value = op.get("value")
        
        # Parse path and apply operation
        current_spec = _apply_spec_operation(current_spec, operation, path, value)
    
    # Update spec
    workspace.spec = current_spec
    workspace.spec_version += 1
    workspace.last_modified_at = datetime.utcnow()
    
    # Save to history with delta
    history = SpecHistory(
        workspace_id=workspace.id,
        version=workspace.spec_version,
        spec=current_spec,
        delta={"operations": request.operations},
        change_source="user",
        change_notes=request.change_notes
    )
    db.add(history)
    
    db.commit()
    db.refresh(workspace)
    
    return SpecResponse(
        workspace_id=workspace.id,
        spec=workspace.spec,
        version=workspace.spec_version,
        last_modified_at=workspace.last_modified_at
    )


@router.get("/{workspace_id}/spec/history")
async def get_spec_history(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get spec version history for a workspace
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Get total count
    total = db.query(func.count(SpecHistory.id)).filter(
        SpecHistory.workspace_id == workspace.id
    ).scalar()
    
    # Get history entries
    history = db.query(SpecHistory).filter(
        SpecHistory.workspace_id == workspace.id
    ).order_by(
        SpecHistory.version.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "history": [SpecHistoryResponse.model_validate(h) for h in history],
        "total": total
    }


@router.post("/{workspace_id}/spec/rollback/{version}")
async def rollback_spec(
    workspace_id: UUID,
    version: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rollback spec to a previous version
    
    Creates a new version with the old spec content.
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Find the target version
    target_history = db.query(SpecHistory).filter(
        SpecHistory.workspace_id == workspace.id,
        SpecHistory.version == version
    ).first()
    
    if not target_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found"
        )
    
    # Update spec
    workspace.spec = target_history.spec
    workspace.spec_version += 1
    workspace.last_modified_at = datetime.utcnow()
    
    # Save as new version
    history = SpecHistory(
        workspace_id=workspace.id,
        version=workspace.spec_version,
        spec=target_history.spec,
        change_source="rollback",
        change_notes=f"Rollback to version {version}"
    )
    db.add(history)
    
    db.commit()
    db.refresh(workspace)
    
    return SpecResponse(
        workspace_id=workspace.id,
        spec=workspace.spec,
        version=workspace.spec_version,
        last_modified_at=workspace.last_modified_at
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _apply_spec_operation(spec: dict, operation: str, path: str, value=None) -> dict:
    """
    Apply a single operation to a spec
    
    Supports:
    - add: Add a value at path
    - update: Update value at path
    - remove: Remove value at path
    """
    import re
    
    if not path:
        if operation in ("add", "update"):
            return value
        else:
            return {}
    
    # Parse path: "items[0].rarity" -> ["items", 0, "rarity"]
    parts = []
    for part in re.split(r'\.|\[|\]', path):
        if part:
            parts.append(int(part) if part.isdigit() else part)
    
    # Navigate to parent
    current = spec
    for i, part in enumerate(parts[:-1]):
        if isinstance(part, int):
            # Array index
            while len(current) <= part:
                current.append({})
            current = current[part]
        else:
            # Object key
            if part not in current:
                next_part = parts[i + 1] if i + 1 < len(parts) else None
                current[part] = [] if isinstance(next_part, int) else {}
            current = current[part]
    
    # Apply operation
    final_key = parts[-1]
    
    if operation == "add" or operation == "update":
        if isinstance(final_key, int):
            while len(current) <= final_key:
                current.append(None)
            current[final_key] = value
        else:
            current[final_key] = value
    elif operation == "remove":
        if isinstance(final_key, int):
            if final_key < len(current):
                del current[final_key]
        else:
            if final_key in current:
                del current[final_key]
    
    return spec

