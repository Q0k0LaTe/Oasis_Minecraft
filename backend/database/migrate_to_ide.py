"""
Database migration script for IDE architecture upgrade

This script:
1. Creates new tables: workspaces, conversations, messages, runs, run_events, artifacts, assets, spec_history
2. Preserves existing tables: users, sessions (for auth)
3. Removes old tables: jobs, messages (data is not migrated as the new models are incompatible)

Run this script after updating models.py:
    python -m database.migrate_to_ide
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text
from database.base import engine, Base
from database.models import (
    User,
    UserSession,
    Workspace,
    Conversation,
    Message,
    Run,
    RunEvent,
    Artifact,
    Asset,
    SpecHistory,
)


def get_existing_tables():
    """Get list of existing tables in the database"""
    inspector = inspect(engine)
    return inspector.get_table_names()


def drop_old_tables():
    """Drop old tables that are being replaced"""
    old_tables = ["jobs", "messages"]  # Drop old jobs and messages tables
    
    existing = get_existing_tables()
    
    with engine.connect() as conn:
        for table in old_tables:
            if table in existing:
                print(f"Dropping old table: {table}")
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        conn.commit()


def create_new_tables():
    """Create new tables"""
    new_tables = [
        "workspaces",
        "conversations",
        "messages",
        "runs",
        "run_events",
        "artifacts",
        "assets",
        "spec_history",
    ]
    
    existing = get_existing_tables()
    
    # Create all tables that don't exist
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    
    # Report what was created
    new_existing = get_existing_tables()
    for table in new_tables:
        if table in new_existing and table not in existing:
            print(f"  Created: {table}")
        elif table in new_existing:
            print(f"  Already exists: {table}")
        else:
            print(f"  Failed to create: {table}")


def verify_schema():
    """Verify the schema is correct"""
    inspector = inspect(engine)
    
    print("\nVerifying schema...")
    
    required_tables = [
        "users",
        "sessions",
        "workspaces",
        "conversations",
        "messages",
        "runs",
        "run_events",
        "artifacts",
        "assets",
        "spec_history",
    ]
    
    existing = get_existing_tables()
    
    all_good = True
    for table in required_tables:
        if table in existing:
            columns = [col["name"] for col in inspector.get_columns(table)]
            print(f"  ✓ {table}: {len(columns)} columns")
        else:
            print(f"  ✗ {table}: MISSING")
            all_good = False
    
    return all_good


def main():
    print("=" * 60)
    print("Minecraft Mod Generator - Database Migration to IDE Architecture")
    print("=" * 60)
    
    print("\nStep 1: Check existing tables")
    existing = get_existing_tables()
    print(f"  Found {len(existing)} existing tables: {', '.join(existing)}")
    
    print("\nStep 2: Drop old tables (jobs, messages)")
    drop_old_tables()
    
    print("\nStep 3: Create new tables")
    create_new_tables()
    
    print("\nStep 4: Verify schema")
    if verify_schema():
        print("\n✓ Migration completed successfully!")
    else:
        print("\n✗ Migration completed with errors. Please check the output above.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

