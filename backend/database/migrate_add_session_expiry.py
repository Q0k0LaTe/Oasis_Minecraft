"""
Database migration script to add expires_at field to sessions table

This script adds session expiration support for improved security.

Usage:
    python -m database.migrate_add_session_expiry
    or
    python database/migrate_add_session_expiry.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import text

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_URL, DB_NAME, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
from database.base import engine


def check_column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name AND column_name = :column_name
    """)
    result = conn.execute(query, {"table_name": table_name, "column_name": column_name})
    return result.fetchone() is not None


def migrate_session_expiry():
    """
    Add expires_at column to sessions table
    """
    try:
        print(f"\n📋 Migrating sessions table in database '{DB_NAME}'...")
        
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                # Check if column already exists
                if check_column_exists(conn, 'sessions', 'expires_at'):
                    print("  ℹ️  expires_at column already exists")
                    trans.rollback()
                    return True
                
                print("  ➕ Adding expires_at column to sessions table...")
                
                # Add column with default value (7 days from now for existing sessions)
                default_expiry = datetime.utcnow() + timedelta(days=7)
                conn.execute(text("""
                    ALTER TABLE sessions 
                    ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE NOT NULL 
                    DEFAULT :default_expiry
                """), {"default_expiry": default_expiry})
                
                # Update existing sessions to expire in 7 days from their creation
                print("  🔄 Updating existing sessions with expiry time...")
                conn.execute(text("""
                    UPDATE sessions 
                    SET expires_at = created_at + INTERVAL '7 days'
                    WHERE expires_at = :default_expiry
                """), {"default_expiry": default_expiry})
                
                # Remove the default (new sessions must explicitly set expires_at)
                print("  🔧 Removing default constraint...")
                conn.execute(text("""
                    ALTER TABLE sessions 
                    ALTER COLUMN expires_at DROP DEFAULT
                """))
                
                # Create index for efficient expiry checks
                print("  ➕ Creating index on expires_at...")
                conn.execute(text("""
                    CREATE INDEX ix_sessions_expires_at ON sessions(expires_at)
                """))
                
                print("  ✅ expires_at column added successfully")
                
                # Commit transaction
                trans.commit()
                print("\n✅ Migration completed successfully!")
                return True
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Main function: Execute database migration
    """
    print("=" * 60)
    print("🚀 Database Migration: Add Session Expiry")
    print("=" * 60)
    print(f"\n📊 Configuration:")
    print(f"   Host: {DB_HOST}:{DB_PORT}")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    print()
    
    if not migrate_session_expiry():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print("\n📝 Changes made:")
    print("   - Added expires_at column to sessions table")
    print("   - Existing sessions set to expire 7 days from creation")
    print("   - Created index for efficient expiry lookups")
    print("\n📝 Next steps:")
    print("   1. Restart your backend server")
    print("   2. Test login/logout with new cookie-based auth")


if __name__ == "__main__":
    main()

