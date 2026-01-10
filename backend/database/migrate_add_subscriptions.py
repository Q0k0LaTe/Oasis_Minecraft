"""
Database migration script to add email_subscriptions table

This script creates the email_subscriptions table for product update notifications.

Usage:
    python -m database.migrate_add_subscriptions
    or
    python database/migrate_add_subscriptions.py
"""
import sys
import uuid
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_URL, DB_NAME, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
from database.base import engine


def check_table_exists(conn, table_name):
    """Check if a table exists"""
    query = text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = :table_name
    """)
    result = conn.execute(query, {"table_name": table_name})
    return result.fetchone() is not None


def migrate_subscriptions_table():
    """
    Create email_subscriptions table
    """
    try:
        print(f"\n📋 Migrating email_subscriptions table in database '{DB_NAME}'...")
        
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                # Check if table already exists
                if check_table_exists(conn, 'email_subscriptions'):
                    print("  ℹ️  email_subscriptions table already exists")
                    trans.rollback()
                    return True
                
                print("  ➕ Creating email_subscriptions table...")
                
                # Create table
                conn.execute(text("""
                    CREATE TABLE email_subscriptions (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        status VARCHAR(20) NOT NULL DEFAULT 'subscribed',
                        unsubscribe_token VARCHAR(255) NOT NULL UNIQUE,
                        source VARCHAR(50),
                        utm_source VARCHAR(255),
                        utm_medium VARCHAR(255),
                        utm_campaign VARCHAR(255),
                        utm_term VARCHAR(255),
                        utm_content VARCHAR(255),
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        unsubscribed_at TIMESTAMP WITH TIME ZONE
                    )
                """))
                
                # Create indexes
                print("  ➕ Creating indexes...")
                conn.execute(text("""
                    CREATE INDEX ix_email_subscriptions_email ON email_subscriptions(email)
                """))
                conn.execute(text("""
                    CREATE INDEX ix_email_subscriptions_unsubscribe_token ON email_subscriptions(unsubscribe_token)
                """))
                conn.execute(text("""
                    CREATE INDEX ix_email_subscriptions_status ON email_subscriptions(status)
                """))
                conn.execute(text("""
                    CREATE INDEX ix_email_subscriptions_created_at ON email_subscriptions(created_at)
                """))
                
                print("  ✅ email_subscriptions table created")
                
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
    print("🚀 Database Migration: Add Email Subscriptions Table")
    print("=" * 60)
    print(f"\n📊 Configuration:")
    print(f"   Host: {DB_HOST}:{DB_PORT}")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    print()
    
    if not migrate_subscriptions_table():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Restart your backend server")
    print("   2. Test subscription endpoints")


if __name__ == "__main__":
    main()

