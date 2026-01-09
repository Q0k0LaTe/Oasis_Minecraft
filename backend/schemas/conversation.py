"""
Conversation-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Request schema for creating a conversation"""
    title: Optional[str] = Field(None, max_length=255, description="Conversation title")


class ConversationUpdate(BaseModel):
    """Request schema for updating a conversation"""
    title: Optional[str] = Field(None, max_length=255)


class ConversationResponse(BaseModel):
    """Response schema for a single conversation"""
    id: UUID
    workspace_id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Optional: message count
    message_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response schema for conversation list"""
    conversations: List[ConversationResponse]
    total: int

