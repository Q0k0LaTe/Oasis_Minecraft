"""
Conversations Router
FastAPI routes for conversation and message management
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, Workspace, Conversation, Message, Run, User, UserSession
from auth.dependencies import get_current_user
from schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
)
from schemas.message import (
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    SendMessageResponse,
)

router = APIRouter(tags=["conversations"])


# ============================================================================
# Auth Helpers
# ============================================================================
# Using unified authentication dependency from auth.dependencies
# Supports both query parameter (backward compatible) and Authorization header


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


def get_conversation_or_404(conversation_id: UUID, user: User, db: Session) -> Conversation:
    """Get conversation by ID, ensuring user has access"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check workspace access
    workspace = db.query(Workspace).filter(Workspace.id == conversation.workspace_id).first()
    if not workspace or workspace.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return conversation


# ============================================================================
# Conversation CRUD
# ============================================================================

@router.post("/api/workspaces/{workspace_id}/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    workspace_id: UUID,
    request: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation in a workspace
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    conversation = Conversation(
        workspace_id=workspace.id,
        title=request.title
    )
    
    db.add(conversation)
    
    # Update workspace last_modified_at
    workspace.last_modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conversation)
    
    # Get message count
    message_count = db.query(func.count(Message.id)).filter(
        Message.conversation_id == conversation.id
    ).scalar()
    
    response = ConversationResponse.model_validate(conversation)
    response.message_count = message_count
    
    return response


@router.get("/api/workspaces/{workspace_id}/conversations", response_model=ConversationListResponse)
async def list_conversations(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all conversations in a workspace
    """
    workspace = get_workspace_or_404(workspace_id, user, db)
    
    # Get total count
    total = db.query(func.count(Conversation.id)).filter(
        Conversation.workspace_id == workspace.id
    ).scalar()
    
    # Get conversations
    conversations = db.query(Conversation).filter(
        Conversation.workspace_id == workspace.id
    ).order_by(
        Conversation.updated_at.desc()
    ).offset(skip).limit(limit).all()
    
    # Build response with message counts
    responses = []
    for conv in conversations:
        message_count = db.query(func.count(Message.id)).filter(
            Message.conversation_id == conv.id
        ).scalar()
        
        response = ConversationResponse.model_validate(conv)
        response.message_count = message_count
        responses.append(response)
    
    return ConversationListResponse(
        conversations=responses,
        total=total
    )


@router.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single conversation by ID
    """
    conversation = get_conversation_or_404(conversation_id, user, db)
    
    message_count = db.query(func.count(Message.id)).filter(
        Message.conversation_id == conversation.id
    ).scalar()
    
    response = ConversationResponse.model_validate(conversation)
    response.message_count = message_count
    
    return response


@router.patch("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update conversation metadata (title)
    """
    conversation = get_conversation_or_404(conversation_id, user, db)
    
    if request.title is not None:
        conversation.title = request.title
    
    db.commit()
    db.refresh(conversation)
    
    response = ConversationResponse.model_validate(conversation)
    return response


@router.delete("/api/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its messages
    """
    conversation = get_conversation_or_404(conversation_id, user, db)
    
    db.delete(conversation)
    db.commit()
    
    return None


# ============================================================================
# Message CRUD
# ============================================================================

@router.get("/api/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def list_messages(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all messages in a conversation
    
    Messages are returned in chronological order (oldest first).
    """
    conversation = get_conversation_or_404(conversation_id, user, db)
    
    # Get total count
    total = db.query(func.count(Message.id)).filter(
        Message.conversation_id == conversation.id
    ).scalar()
    
    # Get messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(
        Message.created_at
    ).offset(skip).limit(limit).all()
    
    return MessageListResponse(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        conversation_id=conversation.id
    )


@router.post("/api/conversations/{conversation_id}/messages", response_model=SendMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: UUID,
    request: MessageCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a user message to a conversation
    
    If trigger_run=True (default), this will:
    1. Create the user message
    2. Create a Run in 'queued' status
    3. Start the run in background
    4. Return the message and run_id
    
    The run will:
    - Emit events as it progresses
    - Eventually create an assistant message with results
    """
    conversation = get_conversation_or_404(conversation_id, user, db)
    
    # Get workspace
    workspace = db.query(Workspace).filter(
        Workspace.id == conversation.workspace_id
    ).first()
    
    # Create user message
    message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.content,
        content_type=request.content_type,
        meta_data=request.metadata
    )
    db.add(message)
    
    # Update timestamps
    conversation.updated_at = datetime.utcnow()
    workspace.last_modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    
    run_id = None
    run_status = None
    
    # Create and start run if requested
    if request.trigger_run:
        run = Run(
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            trigger_message_id=message.id,
            run_type=request.run_type,
            status="queued"
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        run_id = run.id
        run_status = run.status
        
        # Start run in background
        from services.run_service import execute_run
        background_tasks.add_task(execute_run, str(run.id))
    
    return SendMessageResponse(
        message=MessageResponse.model_validate(message),
        run_id=run_id,
        run_status=run_status
    )


@router.get("/api/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single message by ID
    """
    
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check access via conversation
    conversation = get_conversation_or_404(message.conversation_id, user, db)
    
    return MessageResponse.model_validate(message)

