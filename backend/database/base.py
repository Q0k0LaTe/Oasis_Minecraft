"""
Database connection and session management using SQLAlchemy
Base configuration for database engine and session factory
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from config import DATABASE_URL

# Create SQLAlchemy engine
# echo=True can print SQL statements in development, should be False in production
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True to see all SQL queries (for debugging)
    pool_pre_ping=True,  # Connection pool automatically detects and reconnects failed connections
    pool_size=5,  # Connection pool size
    max_overflow=10,  # Connection pool overflow size
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database session.
    Usage in FastAPI route:
        def my_route(db: Session = Depends(get_db)):
            ...
    
    Reason: FastAPI's dependency injection system automatically manages database session lifecycle
    - Creates session when request starts
    - Closes session when request ends
    - Ensures no database connection leaks
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

