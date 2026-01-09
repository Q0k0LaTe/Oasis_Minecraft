"""
Workspace-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    """Request schema for creating a workspace"""
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    description: Optional[str] = Field(None, max_length=1000, description="Workspace description")
    cover_image_url: Optional[str] = Field(None, max_length=500, description="Cover image URL")
    
    # Optional initial spec
    spec: Optional[Dict[str, Any]] = Field(None, description="Initial mod spec (JSON)")


class WorkspaceUpdate(BaseModel):
    """Request schema for updating a workspace"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    cover_image_url: Optional[str] = Field(None, max_length=500)


class WorkspaceResponse(BaseModel):
    """Response schema for a single workspace"""
    id: UUID
    owner_id: int
    name: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    spec_version: int
    last_modified_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # Optional: include spec in response
    spec: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class WorkspaceListResponse(BaseModel):
    """Response schema for workspace list"""
    workspaces: List[WorkspaceResponse]
    total: int


class SpecUpdate(BaseModel):
    """Request schema for full spec update (PUT)"""
    spec: Dict[str, Any] = Field(..., description="Complete mod spec (JSON)")
    change_notes: Optional[str] = Field(None, description="Description of changes")


class SpecPatch(BaseModel):
    """Request schema for partial spec update (PATCH)"""
    # JSON Patch style operations
    operations: List[Dict[str, Any]] = Field(
        ...,
        description="List of patch operations: [{op: 'add'|'update'|'remove', path: '...', value: ...}]"
    )
    change_notes: Optional[str] = Field(None, description="Description of changes")


class SpecResponse(BaseModel):
    """Response schema for spec"""
    workspace_id: UUID
    spec: Dict[str, Any]
    version: int
    last_modified_at: datetime
    
    class Config:
        from_attributes = True


class SpecHistoryResponse(BaseModel):
    """Response schema for spec history entry"""
    id: UUID
    version: int
    spec: Dict[str, Any]
    delta: Optional[Dict[str, Any]] = None
    change_source: Optional[str] = None
    change_notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

