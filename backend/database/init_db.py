"""
Database initialization script
Used to create database and table structures for the first time

Usage:
    python -m database.init_db
    or
    python database/init_db.py

Reason:
    - Standalone script, does not depend on main application startup
    - Can be run independently to initialize database
    - Suitable for new projects, directly creates table structures (no migration history needed)
"""
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_URL, DB_NAME, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
from database.base import engine, Base

# Connect to PostgreSQL server (without specifying database) to create database
admin_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"


def create_database_if_not_exists():
    """
    Create database if it does not exist
    
    Reason: PostgreSQL needs to connect to default database first before creating new database
    """
    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": DB_NAME}
            )
            exists = result.fetchone()
            
            if not exists:
                print(f"📦 Creating database '{DB_NAME}'...")
                conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
                print(f"✅ Database '{DB_NAME}' created successfully!")
            else:
                print(f"ℹ️  Database '{DB_NAME}' already exists.")
        
        admin_engine.dispose()
        return True
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        print(f"\nPlease ensure:")
        print(f"  1. PostgreSQL service is running")
        print(f"  2. Database user '{DB_USER}' has permission to create databases")
        print(f"  3. Connection information is correct: {DB_HOST}:{DB_PORT}")
        return False


def init_tables():
    """
    Create all table structures
    
    Reason: Automatically creates tables based on SQLAlchemy models
    """
    try:
        print(f"\n📋 Creating tables in database '{DB_NAME}'...")
        # Import all models to ensure they are registered with Base
        # This ensures all tables are created
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Main function: Execute database initialization process
    """
    print("=" * 60)
    print("🚀 Database Initialization Script")
    print("=" * 60)
    print(f"\n📊 Configuration:")
    print(f"   Host: {DB_HOST}:{DB_PORT}")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    print()
    
    # Step 1: Create database if it does not exist
    if not create_database_if_not_exists():
        sys.exit(1)
    
    # Step 2: Create table structures
    if not init_tables():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Database initialization completed successfully!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Ensure PostgreSQL service is running")
    print("   2. Check database configuration in .env file")
    print("   3. Run 'python -m database.init_db' to initialize database")
    print("   4. Start implementing Phase 2: Authentication core functionality")


if __name__ == "__main__":
    main()

