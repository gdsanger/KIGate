"""
Test script for database migration functionality

This test validates that the database migration properly handles the 
"table jobs has no column named duration" error by adding the missing
duration column to existing jobs tables.
"""
import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path

from database import migrate_database_schema
from model.user import Base


async def test_migration_with_old_database():
    """Test migration functionality with database missing duration column"""
    print("Testing migration with old database schema...")
    
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
        temp_db_path = temp_file.name
    
    try:
        # Create old database schema without duration column
        conn = sqlite3.connect(temp_db_path)
        conn.execute("""
            CREATE TABLE users (
                client_id VARCHAR(36) PRIMARY KEY,
                client_secret VARCHAR(256) NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(200) UNIQUE,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                last_login DATETIME
            )
        """)
        
        conn.execute("""
            CREATE TABLE jobs (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                user_id VARCHAR(36) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                model VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """)
        
        # Insert a test user
        conn.execute("""
            INSERT INTO users (client_id, client_secret, name, email, is_active) 
            VALUES ('test-client-id', 'test-secret', 'Test User', 'test@example.com', 1)
        """)
        
        conn.commit()
        conn.close()
        
        # Verify old schema (no duration column)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        assert 'duration' not in column_names, "Duration column should not exist in old schema"
        print("✓ Confirmed old database schema without duration column")
        
        conn.close()
        
        # Test the migration function directly
        from sqlalchemy import create_engine, text
        engine = create_engine(f"sqlite:///{temp_db_path}")
        
        with engine.connect() as connection:
            migrate_database_schema(connection)
            connection.commit()
        
        # Verify migration added the duration column
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        assert 'duration' in column_names, "Duration column should exist after migration"
        print("✓ Migration successfully added duration column")
        
        conn.close()
        
        # Test that we can now create jobs with duration
        from sqlalchemy import text
        with engine.connect() as connection:
            # Test INSERT with duration column
            connection.execute(text("""
                INSERT INTO jobs (id, name, user_id, provider, model, status, duration) 
                VALUES ('test-job-id', 'test-job', 'test-client-id', 'openai', 'gpt-4', 'created', 100)
            """))
            connection.commit()
            
            # Verify the job was created
            result = connection.execute(text("SELECT id, duration FROM jobs WHERE id = 'test-job-id'")).fetchone()
            assert result is not None, "Job should be created successfully"
            assert result[1] == 100, "Duration should be set correctly"
            print("✓ Successfully created job with duration after migration")
        
        engine.dispose()
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


async def test_migration_with_fresh_database():
    """Test that migration doesn't break fresh database installations"""
    print("\nTesting migration with fresh database schema...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
        temp_db_path = temp_file.name
    
    try:
        # Test with completely fresh database (no tables)
        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{temp_db_path}")
        
        with engine.connect() as connection:
            # Create all tables using SQLAlchemy
            Base.metadata.create_all(connection)
            
            # Run migration (should be safe on fresh database)
            migrate_database_schema(connection)
            connection.commit()
        
        # Verify fresh database has correct schema
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        assert 'duration' in column_names, "Duration column should exist in fresh database"
        print("✓ Fresh database has correct schema with duration column")
        
        conn.close()
        engine.dispose()
        
    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


async def test_migration_idempotency():
    """Test that running migration multiple times is safe"""
    print("\nTesting migration idempotency...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
        temp_db_path = temp_file.name
    
    try:
        # Create database with old schema
        conn = sqlite3.connect(temp_db_path)
        conn.execute("""
            CREATE TABLE jobs (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                user_id VARCHAR(36) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                model VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        
        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{temp_db_path}")
        
        # Run migration multiple times
        for i in range(3):
            with engine.connect() as connection:
                migrate_database_schema(connection)
                connection.commit()
            print(f"✓ Migration run #{i+1} completed successfully")
        
        # Verify only one duration column exists
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        duration_columns = [col for col in columns if col[1] == 'duration']
        
        assert len(duration_columns) == 1, "Should have exactly one duration column"
        print("✓ Multiple migration runs are idempotent")
        
        conn.close()
        engine.dispose()
        
    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


async def main():
    """Run all migration tests"""
    print("Starting database migration tests...\n")
    
    try:
        await test_migration_with_old_database()
        await test_migration_with_fresh_database() 
        await test_migration_idempotency()
        
        print("\n🎉 All database migration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Migration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())