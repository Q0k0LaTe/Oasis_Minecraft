"""
Database migration script: Convert User.id from Integer to UUID

This script:
1. Adds temporary UUID columns for users, sessions, and workspaces
2. Generates UUIDs for all existing users
3. Updates all foreign key references
4. Drops old columns and renames new columns
5. Recreates foreign key constraints

IMPORTANT: This is a destructive migration. Make sure to backup your database first!

Usage:
    python -m database.migrate_user_id_to_uuid
"""
import sys
import uuid
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text, MetaData, Table
from sqlalchemy.engine import Engine
from database.base import engine
from config import DATABASE_URL


def get_table_info(conn, table_name: str):
    """Get column information for a table"""
    result = conn.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table_name
        ORDER BY ordinal_position
    """), {"table_name": table_name})
    return result.fetchall()


def check_current_schema(conn):
    """Check current schema to determine if migration is needed"""
    print("Checking current schema...")
    
    # Check users table
    users_cols = get_table_info(conn, "users")
    user_id_type = None
    for col in users_cols:
        if col[0] == "id":
            user_id_type = col[1]
            break
    
    if user_id_type == "uuid":
        print("  ✓ User.id is already UUID - migration not needed")
        return False
    
    if user_id_type != "integer":
        print(f"  ⚠ Warning: User.id type is {user_id_type}, expected integer")
        return False
    
    print(f"  ✓ User.id is currently {user_id_type} - migration needed")
    return True


def backup_foreign_keys(conn):
    """Backup foreign key constraint information"""
    print("\nBacking up foreign key constraints...")
    
    # Get all foreign keys referencing users.id
    # PostgreSQL uses referential_constraints and constraint_column_usage for FK info
    result = conn.execute(text("""
        SELECT
            tc.constraint_name,
            tc.table_name,
            kcu.column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.referential_constraints AS rc
            ON tc.constraint_name = rc.constraint_name
            AND tc.table_schema = rc.constraint_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON rc.unique_constraint_name = ccu.constraint_name
            AND rc.unique_constraint_schema = ccu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            AND ccu.table_name = 'users'
            AND ccu.column_name = 'id'
    """))
    
    fks = result.fetchall()
    print(f"  Found {len(fks)} foreign key constraints")
    for fk in fks:
        print(f"    - {fk[1]}.{fk[2]} -> users.id ({fk[0]})")
    
    return fks


def drop_foreign_keys(conn, fks):
    """Drop all foreign key constraints"""
    print("\nDropping foreign key constraints...")
    
    for fk in fks:
        constraint_name = fk[0]
        table_name = fk[1]
        try:
            conn.execute(text(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"))
            print(f"  ✓ Dropped {constraint_name} from {table_name}")
        except Exception as e:
            print(f"  ⚠ Warning: Could not drop {constraint_name}: {e}")


def add_temporary_columns(conn):
    """Add temporary UUID columns"""
    print("\nAdding temporary UUID columns...")
    
    # Add id_new to users
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN id_new UUID"))
        print("  ✓ Added users.id_new")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("  ℹ users.id_new already exists")
        else:
            raise
    
    # Add user_id_new to sessions
    try:
        conn.execute(text("ALTER TABLE sessions ADD COLUMN user_id_new UUID"))
        print("  ✓ Added sessions.user_id_new")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("  ℹ sessions.user_id_new already exists")
        else:
            raise
    
    # Add owner_id_new to workspaces
    try:
        conn.execute(text("ALTER TABLE workspaces ADD COLUMN owner_id_new UUID"))
        print("  ✓ Added workspaces.owner_id_new")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("  ℹ workspaces.owner_id_new already exists")
        else:
            raise
    


def generate_uuids_for_users(conn):
    """Generate UUIDs for all existing users and update foreign keys"""
    print("\nGenerating UUIDs for users...")
    
    # Get all users
    result = conn.execute(text("SELECT id FROM users ORDER BY id"))
    users = result.fetchall()
    
    if not users:
        print("  ℹ No users found in database")
        return {}
    
    print(f"  Found {len(users)} users")
    
    # Create mapping: old_id -> new_uuid
    id_mapping = {}
    
    for (old_id,) in users:
        new_uuid = uuid.uuid4()
        id_mapping[old_id] = new_uuid
        
        # Update users table
        conn.execute(
            text("UPDATE users SET id_new = :new_uuid WHERE id = :old_id"),
            {"new_uuid": str(new_uuid), "old_id": old_id}
        )
    
    print(f"  ✓ Generated {len(id_mapping)} UUIDs")
    
    return id_mapping


def update_foreign_keys(conn, id_mapping):
    """Update foreign key references in sessions and workspaces"""
    print("\nUpdating foreign key references...")
    
    # Update sessions.user_id_new
    sessions_updated = 0
    for old_id, new_uuid in id_mapping.items():
        result = conn.execute(
            text("UPDATE sessions SET user_id_new = :new_uuid WHERE user_id = :old_id"),
            {"new_uuid": str(new_uuid), "old_id": old_id}
        )
        sessions_updated += result.rowcount
    
    print(f"  ✓ Updated {sessions_updated} sessions")
    
    # Update workspaces.owner_id_new
    workspaces_updated = 0
    for old_id, new_uuid in id_mapping.items():
        result = conn.execute(
            text("UPDATE workspaces SET owner_id_new = :new_uuid WHERE owner_id = :old_id"),
            {"new_uuid": str(new_uuid), "old_id": old_id}
        )
        workspaces_updated += result.rowcount
    
    print(f"  ✓ Updated {workspaces_updated} workspaces")
    


def swap_columns(conn):
    """Swap old columns with new columns"""
    print("\nSwapping columns...")
    
    # For users table: drop old id, rename id_new to id, set as primary key
    print("  Updating users table...")
    
    # Drop primary key constraint first
    try:
        conn.execute(text("ALTER TABLE users DROP CONSTRAINT users_pkey"))
        print("    ✓ Dropped primary key constraint")
    except Exception as e:
        print(f"    ⚠ Could not drop primary key: {e}")
    
    # Drop old id column
    try:
        conn.execute(text("ALTER TABLE users DROP COLUMN id"))
        print("    ✓ Dropped old id column")
    except Exception as e:
        print(f"    ⚠ Could not drop old id column: {e}")
    
    # Rename id_new to id
    try:
        conn.execute(text("ALTER TABLE users RENAME COLUMN id_new TO id"))
        print("    ✓ Renamed id_new to id")
    except Exception as e:
        print(f"    ⚠ Could not rename column: {e}")
    
    # Set as primary key
    try:
        conn.execute(text("ALTER TABLE users ADD PRIMARY KEY (id)"))
        print("    ✓ Added primary key constraint")
    except Exception as e:
        print(f"    ⚠ Could not add primary key: {e}")
    
    # For sessions table: drop old user_id, rename user_id_new to user_id
    print("  Updating sessions table...")
    try:
        conn.execute(text("ALTER TABLE sessions DROP COLUMN user_id"))
        print("    ✓ Dropped old user_id column")
    except Exception as e:
        print(f"    ⚠ Could not drop old user_id: {e}")
    
    try:
        conn.execute(text("ALTER TABLE sessions RENAME COLUMN user_id_new TO user_id"))
        print("    ✓ Renamed user_id_new to user_id")
    except Exception as e:
        print(f"    ⚠ Could not rename column: {e}")
    
    # For workspaces table: drop old owner_id, rename owner_id_new to owner_id
    print("  Updating workspaces table...")
    try:
        conn.execute(text("ALTER TABLE workspaces DROP COLUMN owner_id"))
        print("    ✓ Dropped old owner_id column")
    except Exception as e:
        print(f"    ⚠ Could not drop old owner_id: {e}")
    
    try:
        conn.execute(text("ALTER TABLE workspaces RENAME COLUMN owner_id_new TO owner_id"))
        print("    ✓ Renamed owner_id_new to owner_id")
    except Exception as e:
        print(f"    ⚠ Could not rename column: {e}")
    


def recreate_foreign_keys(conn):
    """Recreate foreign key constraints"""
    print("\nRecreating foreign key constraints...")
    
    # Recreate sessions.user_id -> users.id
    try:
        conn.execute(text("""
            ALTER TABLE sessions
            ADD CONSTRAINT sessions_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        """))
        print("  ✓ Created sessions.user_id foreign key")
    except Exception as e:
        print(f"  ⚠ Could not create sessions foreign key: {e}")
    
    # Recreate workspaces.owner_id -> users.id
    try:
        conn.execute(text("""
            ALTER TABLE workspaces
            ADD CONSTRAINT workspaces_owner_id_fkey
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        """))
        print("  ✓ Created workspaces.owner_id foreign key")
    except Exception as e:
        print(f"  ⚠ Could not create workspaces foreign key: {e}")
    
    # Recreate indexes
    try:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions(user_id)"))
        print("  ✓ Created sessions.user_id index")
    except Exception as e:
        print(f"  ⚠ Could not create sessions index: {e}")
    
    try:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workspaces_owner_id ON workspaces(owner_id)"))
        print("  ✓ Created workspaces.owner_id index")
    except Exception as e:
        print(f"  ⚠ Could not create workspaces index: {e}")
    


def verify_migration(conn):
    """Verify the migration was successful"""
    print("\nVerifying migration...")
    
    # Check users.id type
    result = conn.execute(text("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'id'
    """))
    user_id_type = result.fetchone()
    
    if user_id_type and user_id_type[0] == "uuid":
        print("  ✓ users.id is now UUID")
    else:
        print(f"  ✗ users.id type is {user_id_type[0] if user_id_type else 'unknown'}")
        return False
    
    # Check sessions.user_id type
    result = conn.execute(text("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sessions' AND column_name = 'user_id'
    """))
    session_user_id_type = result.fetchone()
    
    if session_user_id_type and session_user_id_type[0] == "uuid":
        print("  ✓ sessions.user_id is now UUID")
    else:
        print(f"  ✗ sessions.user_id type is {session_user_id_type[0] if session_user_id_type else 'unknown'}")
        return False
    
    # Check workspaces.owner_id type
    result = conn.execute(text("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'workspaces' AND column_name = 'owner_id'
    """))
    workspace_owner_id_type = result.fetchone()
    
    if workspace_owner_id_type and workspace_owner_id_type[0] == "uuid":
        print("  ✓ workspaces.owner_id is now UUID")
    else:
        print(f"  ✗ workspaces.owner_id type is {workspace_owner_id_type[0] if workspace_owner_id_type else 'unknown'}")
        return False
    
    # Check data integrity
    result = conn.execute(text("""
        SELECT COUNT(*) FROM users
    """))
    user_count = result.fetchone()[0]
    print(f"  ✓ Found {user_count} users")
    
    result = conn.execute(text("""
        SELECT COUNT(*) FROM sessions
    """))
    session_count = result.fetchone()[0]
    print(f"  ✓ Found {session_count} sessions")
    
    result = conn.execute(text("""
        SELECT COUNT(*) FROM workspaces
    """))
    workspace_count = result.fetchone()[0]
    print(f"  ✓ Found {workspace_count} workspaces")
    
    return True


def main():
    """Main migration function"""
    print("=" * 60)
    print("Database Migration: User.id Integer -> UUID")
    print("=" * 60)
    print("\n⚠️  WARNING: This is a destructive migration!")
    print("   Please backup your database before proceeding.")
    print()
    
    response = input("Have you backed up your database? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Migration cancelled. Please backup your database first.")
        return
    
    try:
        # First check if migration is needed (read-only operation)
        with engine.connect() as conn:
            if not check_current_schema(conn):
                print("\n✓ Migration not needed - User.id is already UUID")
                return
        
        # Perform migration in a transaction (auto-commits on success, rolls back on error)
        with engine.begin() as conn:
            # Step 1: Backup foreign keys
            fks = backup_foreign_keys(conn)
            
            # Step 2: Drop foreign keys
            drop_foreign_keys(conn, fks)
            
            # Step 3: Add temporary columns
            add_temporary_columns(conn)
            
            # Step 4: Generate UUIDs and update foreign keys
            id_mapping = generate_uuids_for_users(conn)
            if id_mapping:
                update_foreign_keys(conn, id_mapping)
            
            # Step 5: Swap columns
            swap_columns(conn)
            
            # Step 6: Recreate foreign keys
            recreate_foreign_keys(conn)
            
            # Transaction will auto-commit here if no exception occurred
        
        # Step 7: Verify migration (in a new connection)
        with engine.connect() as conn:
            if verify_migration(conn):
                print("\n" + "=" * 60)
                print("✅ Migration completed successfully!")
                print("=" * 60)
            else:
                print("\n" + "=" * 60)
                print("⚠️  Migration completed with warnings. Please verify manually.")
                print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  Database may be in an inconsistent state. Please restore from backup.")
        sys.exit(1)


if __name__ == "__main__":
    main()

