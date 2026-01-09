"""
Database models (SQLAlchemy ORM models)

Defines database table structures for the new IDE-style architecture:
- User: User accounts
- UserSession: Login session tokens (for authentication)
- Workspace: Minecraft Mod projects (like IDE workspaces)
- Conversation: Chat conversations within a workspace
- Message: Individual messages in a conversation
- Run: Long-running tasks (generation, build)
- RunEvent: Events emitted during a run (for SSE streaming)
- Artifact: Files/outputs produced by runs
- Asset: User-uploaded or selected resources (textures, covers)
- SpecHistory: Versioned spec snapshots
"""
import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


def generate_uuid():
    """Generate a new UUID4"""
    return uuid.uuid4()


class User(Base):
    """
    User table model
    Corresponds to the users table in the design document
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # bcrypt hashed password (nullable for Google OAuth users)
    google_id = Column(String(255), unique=True, nullable=True, index=True)  # Google account unique identifier
    auth_provider = Column(String(20), default='email', nullable=False)  # 'email' or 'google'
    avatar_url = Column(String(500), nullable=True)  # User avatar URL from Google
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class UserSession(Base):
    """
    Login Session table model
    Used for authentication tokens (like JWT sessions)
    
    Note: This is NOT the conversation session - that's now handled by Workspace + Conversation
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)  # UUID format token
    name = Column(String(255), nullable=True)  # Optional: session name for user identification
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user_agent = Column(Text, nullable=True)  # Optional: record login device information
    ip_address = Column(String(45), nullable=True)  # Optional: record IP address
    is_active = Column(Boolean, default=True)  # Can be used to actively delete session

    # Relationship definitions
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, token='{self.session_token[:8]}...')>"


class Workspace(Base):
    """
    Workspace model - represents a Minecraft Mod project
    
    Similar to an IDE workspace/project. Contains:
    - The canonical mod spec (JSON)
    - Conversations about the project
    - Runs (generation/build tasks)
    - Assets (textures, covers)
    """
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    
    # Canonical mod spec (JSON) - the source of truth for user intent
    spec = Column(JSONB, nullable=True)
    spec_version = Column(Integer, default=0)  # Incremented on each spec update
    
    # Timestamps
    last_modified_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="workspaces")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="workspace", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="workspace", cascade="all, delete-orphan")
    spec_history = relationship("SpecHistory", back_populates="workspace", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"


class Conversation(Base):
    """
    Conversation model - a chat thread within a workspace
    
    Similar to a chat conversation in ChatGPT, but scoped to a workspace.
    Users can have multiple conversations per workspace.
    """
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=True)  # Auto-generated or user-set title
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    def __repr__(self):
        return f"<Conversation(id={self.id}, workspace_id={self.workspace_id}, title='{self.title}')>"


class Message(Base):
    """
    Message model - individual messages in a conversation
    
    Supports multiple roles:
    - user: User input
    - assistant: AI response
    - system: System messages
    - tool: Tool call results
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=True)  # Text content or JSON string
    content_type = Column(String(50), default="text")  # text, json, markdown
    
    # Optional: link to the run that produced this message (for assistant responses)
    trigger_run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Metadata
    meta_data = Column(JSONB, nullable=True)  # Additional info (tool calls, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    trigger_run = relationship("Run", back_populates="result_messages", foreign_keys=[trigger_run_id])

    def __repr__(self):
        content_preview = (self.content[:30] + '...') if self.content and len(self.content) > 30 else self.content
        return f"<Message(id={self.id}, role='{self.role}', content='{content_preview}')>"


class Run(Base):
    """
    Run model - represents a long-running task execution
    
    Triggered by a user message, a Run can:
    - Generate mod code and assets
    - Build the mod (compile to JAR)
    - Emit events during execution (for SSE streaming)
    - Produce artifacts (JARs, textures, code)
    """
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # The message that triggered this run
    trigger_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Run type: generate, build, regenerate_texture, etc.
    run_type = Column(String(50), nullable=False, default="generate")
    
    # Status: queued, running, succeeded, failed, canceled
    status = Column(String(50), nullable=False, default="queued")
    progress = Column(Integer, default=0)  # 0-100 progress percentage
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error info (if failed)
    error = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)  # Stack trace, additional context
    
    # Result summary
    result = Column(JSONB, nullable=True)  # Summary of what was produced
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="runs")
    conversation = relationship("Conversation", foreign_keys=[conversation_id])
    trigger_message = relationship("Message", foreign_keys=[trigger_message_id])
    result_messages = relationship("Message", back_populates="trigger_run", foreign_keys=[Message.trigger_run_id])
    events = relationship("RunEvent", back_populates="run", cascade="all, delete-orphan", order_by="RunEvent.created_at")
    artifacts = relationship("Artifact", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Run(id={self.id}, type='{self.run_type}', status='{self.status}')>"


class RunEvent(Base):
    """
    RunEvent model - events emitted during run execution
    
    Used for real-time updates via SSE/WebSocket.
    Event types include:
    - run.status: Status changes (queued→running→succeeded)
    - log.append: Log messages
    - spec.preview / spec.patch / spec.saved: Spec updates
    - asset.generated / asset.selected: Asset events
    - artifact.created: New artifact available
    - task.started / task.finished: Pipeline task events
    """
    __tablename__ = "run_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    event_type = Column(String(100), nullable=False)  # run.status, log.append, spec.preview, etc.
    payload = Column(JSONB, nullable=True)  # Event-specific data
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    run = relationship("Run", back_populates="events")

    # Index for efficient event retrieval
    __table_args__ = (
        Index('ix_run_events_run_id_created_at', 'run_id', 'created_at'),
    )

    def __repr__(self):
        return f"<RunEvent(id={self.id}, run_id={self.run_id}, type='{self.event_type}')>"


class Artifact(Base):
    """
    Artifact model - files/outputs produced by runs
    
    Types include:
    - jar: Compiled mod JAR file
    - texture: Generated texture PNG
    - code: Generated source code
    - model: Minecraft model JSON
    """
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    artifact_type = Column(String(50), nullable=False)  # jar, texture, code, model
    file_path = Column(String(500), nullable=False)  # Relative path from workspace root
    file_name = Column(String(255), nullable=False)  # Display name
    file_size = Column(Integer, nullable=True)  # Size in bytes
    mime_type = Column(String(100), nullable=True)
    
    # Metadata
    meta_data = Column(JSONB, nullable=True)  # Additional info (mod_id, version, etc.)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    run = relationship("Run", back_populates="artifacts")
    workspace = relationship("Workspace", back_populates="artifacts")

    def __repr__(self):
        return f"<Artifact(id={self.id}, type='{self.artifact_type}', file='{self.file_name}')>"


class Asset(Base):
    """
    Asset model - user-uploaded or selected resources
    
    Types include:
    - cover: Workspace cover image
    - texture: Block/item/tool texture
    - reference: Reference image for texture generation
    """
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    asset_type = Column(String(50), nullable=False)  # cover, texture, reference
    file_path = Column(String(500), nullable=False)  # Relative path from assets root
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=True)
    
    # Binding info (for textures bound to blocks/items/tools)
    target_type = Column(String(50), nullable=True)  # block, item, tool
    target_id = Column(String(100), nullable=True)  # The block/item/tool id in spec
    
    # Metadata
    meta_data = Column(JSONB, nullable=True)  # Additional info
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="assets")

    # Index for efficient lookup
    __table_args__ = (
        Index('ix_assets_workspace_target', 'workspace_id', 'target_type', 'target_id'),
    )

    def __repr__(self):
        return f"<Asset(id={self.id}, type='{self.asset_type}', target='{self.target_type}:{self.target_id}')>"


class SpecHistory(Base):
    """
    SpecHistory model - versioned snapshots of workspace specs
    
    Tracks changes to the mod specification for:
    - Undo/redo functionality
    - Audit trail
    - Diff viewing
    """
    __tablename__ = "spec_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    version = Column(Integer, nullable=False)  # Sequential version number
    spec = Column(JSONB, nullable=False)  # Full spec snapshot
    delta = Column(JSONB, nullable=True)  # Delta that was applied (optional)
    
    # Who/what made the change
    change_source = Column(String(50), nullable=True)  # user, ai, build, rollback
    change_notes = Column(Text, nullable=True)  # Description of change
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="spec_history")

    # Index for efficient version lookup
    __table_args__ = (
        Index('ix_spec_history_workspace_version', 'workspace_id', 'version'),
    )

    def __repr__(self):
        return f"<SpecHistory(workspace_id={self.workspace_id}, version={self.version})>"
