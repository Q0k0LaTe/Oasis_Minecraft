"""
Asset-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    """Request schema for creating/uploading an asset"""
    asset_type: Literal["cover", "texture", "reference"] = Field(..., description="Asset type")
    file_name: str = Field(..., max_length=255, description="Original file name")
    mime_type: Optional[str] = Field(None, description="MIME type")
    
    # Optional binding info
    target_type: Optional[Literal["block", "item", "tool"]] = Field(None, description="Target element type")
    target_id: Optional[str] = Field(None, max_length=100, description="Target element ID in spec")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AssetResponse(BaseModel):
    """Response schema for an asset"""
    id: UUID
    workspace_id: UUID
    
    asset_type: str  # cover, texture, reference
    file_path: str
    file_name: str
    mime_type: Optional[str] = None
    
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    
    metadata: Optional[Dict[str, Any]] = Field(None, alias="meta_data")
    
    # Generated URLs
    url: Optional[str] = None  # Direct access URL
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True


class AssetListResponse(BaseModel):
    """Response schema for asset list"""
    assets: List[AssetResponse]
    total: int


class AssetSelectRequest(BaseModel):
    """Request schema for binding an asset to a spec element"""
    asset_id: UUID = Field(..., description="Asset ID to bind")
    target_type: Literal["block", "item", "tool"] = Field(..., description="Target element type")
    target_id: str = Field(..., max_length=100, description="Target element ID in spec")


class AssetSelectResponse(BaseModel):
    """Response schema for asset selection"""
    success: bool
    asset: AssetResponse
    message: str

