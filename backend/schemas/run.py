"""
Run-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class RunResponse(BaseModel):
    """Response schema for a single run"""
    id: UUID
    workspace_id: UUID
    conversation_id: Optional[UUID] = None
    trigger_message_id: Optional[UUID] = None
    
    run_type: str  # generate, build, regenerate_texture
    status: str  # queued, running, succeeded, failed, canceled
    progress: int = 0  # 0-100
    
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    result: Optional[Dict[str, Any]] = None
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class RunListResponse(BaseModel):
    """Response schema for run list"""
    runs: List[RunResponse]
    total: int


class RunEventResponse(BaseModel):
    """Response schema for a run event"""
    id: UUID
    run_id: UUID
    event_type: str  # run.status, log.append, spec.preview, etc.
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ArtifactResponse(BaseModel):
    """Response schema for an artifact"""
    id: UUID
    run_id: UUID
    workspace_id: UUID
    
    artifact_type: str  # jar, texture, code, model
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    
    metadata: Optional[Dict[str, Any]] = Field(None, alias="meta_data")
    download_url: Optional[str] = None  # Generated download URL
    
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True


class ArtifactListResponse(BaseModel):
    """Response schema for artifact list"""
    artifacts: List[ArtifactResponse]
    total: int

