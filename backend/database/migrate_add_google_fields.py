"""
Database migration script to add Google OAuth fields to users table

This script adds the following columns to the users table:
- google_id (String, unique, nullable)
- auth_provider (String, default='email')
- avatar_url (String, nullable)
- Makes password_hash nullable

Usage:
    python -m database.migrate_add_google_fields
    or
    python database/migrate_add_google_fields.py
"""
import sys
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_URL, DB_NAME, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
from database.base import engine

# Connect to PostgreSQL server (without specifying database) to create database
admin_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"


def check_column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name AND column_name = :column_name
    """)
    result = conn.execute(query, {"table_name": table_name, "column_name": column_name})
    return result.fetchone() is not None


def migrate_users_table():
    """
    Add Google OAuth fields to users table
    """
    try:
        print(f"\n📋 Migrating users table in database '{DB_NAME}'...")
        
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                # Check if columns already exist
                has_google_id = check_column_exists(conn, 'users', 'google_id')
                has_auth_provider = check_column_exists(conn, 'users', 'auth_provider')
                has_avatar_url = check_column_exists(conn, 'users', 'avatar_url')
                
                # Add google_id column
                if not has_google_id:
                    print("  ➕ Adding google_id column...")
                    conn.execute(text("""
                        ALTER TABLE users 
                        ADD COLUMN google_id VARCHAR(255) UNIQUE
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id)
                    """))
                    print("  ✅ google_id column added")
                else:
                    print("  ℹ️  google_id column already exists")
                
                # Add auth_provider column
                if not has_auth_provider:
                    print("  ➕ Adding auth_provider column...")
                    conn.execute(text("""
                        ALTER TABLE users 
                        ADD COLUMN auth_provider VARCHAR(20) NOT NULL DEFAULT 'email'
                    """))
                    print("  ✅ auth_provider column added")
                else:
                    print("  ℹ️  auth_provider column already exists")
                
                # Add avatar_url column
                if not has_avatar_url:
                    print("  ➕ Adding avatar_url column...")
                    conn.execute(text("""
                        ALTER TABLE users 
                        ADD COLUMN avatar_url VARCHAR(500)
                    """))
                    print("  ✅ avatar_url column added")
                else:
                    print("  ℹ️  avatar_url column already exists")
                
                # Make password_hash nullable (if it's not already)
                print("  🔄 Checking password_hash column...")
                result = conn.execute(text("""
                    SELECT is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'password_hash'
                """))
                row = result.fetchone()
                if row and row[0] == 'NO':
                    print("  ➕ Making password_hash nullable...")
                    conn.execute(text("""
                        ALTER TABLE users 
                        ALTER COLUMN password_hash DROP NOT NULL
                    """))
                    print("  ✅ password_hash is now nullable")
                else:
                    print("  ℹ️  password_hash is already nullable")
                
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
    print("🚀 Database Migration: Add Google OAuth Fields")
    print("=" * 60)
    print(f"\n📊 Configuration:")
    print(f"   Host: {DB_HOST}:{DB_PORT}")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    print()
    
    if not migrate_users_table():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Restart your backend server")
    print("   2. Test Google OAuth login")


if __name__ == "__main__":
    main()

