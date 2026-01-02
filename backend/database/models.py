"""
Database models (SQLAlchemy ORM models)
Defines database table structures for users, sessions, and jobs tables
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class User(Base):
    """
    User table model
    Corresponds to the users table in the design document
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hashed password
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationship: one user can have multiple sessions and jobs
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class UserSession(Base):
    """
    Session table model
    Corresponds to the sessions table in the design document
    Similar to ChatGPT's conversation - never expires, users can create multiple sessions
    
    Note: Class name uses UserSession to avoid conflict with SQLAlchemy's Session class
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
    jobs = relationship("Job", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, token='{self.session_token[:8]}...', name='{self.name}')>"


class Job(Base):
    """
    Job table model
    Corresponds to the jobs table in the design document
    Stores mod generation tasks, migrated from in-memory storage to database
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(255), unique=True, nullable=False, index=True)  # Existing UUID format job_id for compatibility
    status = Column(String(50), nullable=False)  # queued, analyzing, generating, completed, failed, etc.
    progress = Column(Integer, default=0)  # Progress percentage 0-100
    spec = Column(JSONB, nullable=True)  # AI-generated spec information (JSON format)
    result = Column(JSONB, nullable=True)  # Final generation result (JSON format)
    logs = Column(JSONB, nullable=True)  # Log array (JSON format)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship definitions
    user = relationship("User", back_populates="jobs")
    session = relationship("UserSession", back_populates="jobs")

    def __repr__(self):
        return f"<Job(id={self.id}, job_id='{self.job_id}', status='{self.status}', progress={self.progress})>"

