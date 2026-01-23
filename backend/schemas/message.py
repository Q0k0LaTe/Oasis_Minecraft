"""
Message-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Request schema for creating a message (user message)"""
    content: str = Field(..., min_length=1, description="Message content")
    content_type: Literal["text", "json", "markdown"] = Field("text", description="Content format")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    # Whether to trigger a run after creating this message
    trigger_run: bool = Field(True, description="Whether to start a generation run")
    run_type: Literal["generate", "build"] = Field("generate", description="Type of run to trigger")


class MessageResponse(BaseModel):
    """Response schema for a single message"""
    id: UUID
    conversation_id: UUID
    role: str  # user, assistant, system, tool
    content: Optional[str] = None
    content_type: str = "text"
    trigger_run_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = Field(None, alias="meta_data")
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True


class MessageListResponse(BaseModel):
    """Response schema for message list"""
    messages: List[MessageResponse]
    total: int
    conversation_id: UUID


class SendMessageResponse(BaseModel):
    """Response schema for sending a message (includes triggered run info)"""
    message: MessageResponse
    run_id: Optional[UUID] = Field(None, description="ID of the triggered run (if trigger_run=True)")
    run_status: Optional[str] = Field(None, description="Initial run status")

