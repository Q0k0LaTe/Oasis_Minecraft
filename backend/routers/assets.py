"""
Assets Router
FastAPI routes for asset management (textures, covers, etc.)
"""
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, Workspace, Asset, User, UserSession
from schemas.asset import (
    AssetResponse,
    AssetListResponse,
    AssetSelectRequest,
    AssetSelectResponse,
)
from config import BASE_DIR

router = APIRouter(prefix="/api", tags=["assets"])

# Asset storage directory
ASSETS_DIR = BASE_DIR / "assets_storage"
ASSETS_DIR.mkdir(exist_ok=True)


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


def get_workspace_or_404(workspace_id: UUID, user: User, db: Session) -> Workspace:
    """Get workspace by ID, ensuring user has access"""
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
    
    return workspace


# ============================================================================
# Asset Upload & Management
# ============================================================================

@router.post("/workspaces/{workspace_id}/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    workspace_id: UUID,
    session_token: str,
    file: UploadFile = File(...),
    asset_type: str = Form(...),  # cover, texture, reference
    target_type: Optional[str] = Form(None),  # block, item, tool
    target_id: Optional[str] = Form(None),  # spec element id
    db: Session = Depends(get_db)
):
    """
    Upload an asset (texture, cover, etc.) to a workspace
    
    Supported asset types:
    - cover: Workspace cover image
    - texture: Block/item/tool texture (16x16 PNG recommended)
    - reference: Reference image for texture generation
    
    For textures, optionally specify target_type and target_id to bind
    the asset to a specific block/item/tool in the spec.
    """
    user = await get_current_user(session_token, db)
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Validate asset type
    if asset_type not in ("cover", "texture", "reference"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid asset type. Must be: cover, texture, or reference"
        )
    
    # Validate target_type if provided
    if target_type and target_type not in ("block", "item", "tool"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target type. Must be: block, item, or tool"
        )
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Create workspace asset directory
    workspace_dir = ASSETS_DIR / str(workspace_id)
    workspace_dir.mkdir(exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix if file.filename else ".png"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = workspace_dir / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Create asset record
    asset = Asset(
        workspace_id=workspace.id,
        asset_type=asset_type,
        file_path=str(file_path.relative_to(ASSETS_DIR)),
        file_name=file.filename or unique_filename,
        mime_type=file.content_type,
        target_type=target_type,
        target_id=target_id
    )
    
    db.add(asset)
    
    # Update workspace last_modified_at
    workspace.last_modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(asset)
    
    response = AssetResponse.model_validate(asset)
    response.url = f"/api/assets/{asset.id}"
    
    return response


@router.get("/workspaces/{workspace_id}/assets", response_model=AssetListResponse)
async def list_assets(
    workspace_id: UUID,
    session_token: str,
    asset_type: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List assets for a workspace
    
    Optional filters:
    - asset_type: Filter by type (cover, texture, reference)
    - target_type: Filter by target type (block, item, tool)
    - target_id: Filter by target element ID
    """
    user = await get_current_user(session_token, db)
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Build query
    query = db.query(Asset).filter(Asset.workspace_id == workspace.id)
    
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if target_type:
        query = query.filter(Asset.target_type == target_type)
    if target_id:
        query = query.filter(Asset.target_id == target_id)
    
    # Get total count
    total = query.count()
    
    # Get assets
    assets = query.order_by(Asset.created_at.desc()).offset(skip).limit(limit).all()
    
    # Build responses with URLs
    responses = []
    for asset in assets:
        response = AssetResponse.model_validate(asset)
        response.url = f"/api/assets/{asset.id}"
        responses.append(response)
    
    return AssetListResponse(
        assets=responses,
        total=total
    )


@router.post("/workspaces/{workspace_id}/assets/select", response_model=AssetSelectResponse)
async def select_asset(
    workspace_id: UUID,
    request: AssetSelectRequest,
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Bind an asset to a spec element (block/item/tool)
    
    This updates the asset's target_type and target_id to associate it
    with a specific element in the workspace spec.
    """
    user = await get_current_user(session_token, db)
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Find the asset
    asset = db.query(Asset).filter(
        Asset.id == request.asset_id,
        Asset.workspace_id == workspace.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Unbind any existing asset for this target
    existing = db.query(Asset).filter(
        Asset.workspace_id == workspace.id,
        Asset.target_type == request.target_type,
        Asset.target_id == request.target_id,
        Asset.id != asset.id
    ).first()
    
    if existing:
        existing.target_type = None
        existing.target_id = None
    
    # Bind the new asset
    asset.target_type = request.target_type
    asset.target_id = request.target_id
    asset.updated_at = datetime.utcnow()
    
    # Update workspace last_modified_at
    workspace.last_modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(asset)
    
    response = AssetResponse.model_validate(asset)
    response.url = f"/api/assets/{asset.id}"
    
    return AssetSelectResponse(
        success=True,
        asset=response,
        message=f"Asset bound to {request.target_type}:{request.target_id}"
    )


@router.get("/assets/{asset_id}")
async def get_asset_file(
    asset_id: UUID,
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Get an asset file by ID
    
    Returns the actual file for display/download.
    """
    user = await get_current_user(session_token, db)
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Check workspace access
    workspace = db.query(Workspace).filter(Workspace.id == asset.workspace_id).first()
    if not workspace or workspace.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get file path
    file_path = ASSETS_DIR / asset.file_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not found"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=asset.file_name,
        media_type=asset.mime_type or "application/octet-stream"
    )


@router.get("/assets/{asset_id}/info", response_model=AssetResponse)
async def get_asset_info(
    asset_id: UUID,
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Get asset metadata (without file content)
    """
    user = await get_current_user(session_token, db)
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Check workspace access
    workspace = db.query(Workspace).filter(Workspace.id == asset.workspace_id).first()
    if not workspace or workspace.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    response = AssetResponse.model_validate(asset)
    response.url = f"/api/assets/{asset.id}"
    
    return response


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Delete an asset
    
    Removes both the database record and the file.
    """
    user = await get_current_user(session_token, db)
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Check workspace access
    workspace = db.query(Workspace).filter(Workspace.id == asset.workspace_id).first()
    if not workspace or workspace.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Delete file
    file_path = ASSETS_DIR / asset.file_path
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception:
            pass  # File deletion failure is not critical
    
    # Delete record
    db.delete(asset)
    db.commit()
    
    return None

