"""
Database configuration and setup for KIGate API
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from model.user import Base
# Import Job model to ensure it's registered with Base
from model.job import Job
# Import ApplicationUser model to ensure it's registered with Base
from model.application_user import ApplicationUser
# Import GitHubIssueRecord model to ensure it's registered with Base
from model.github_issue_record import GitHubIssueRecord
# Import Repository model to ensure it's registered with Base
from model.repository import Repository
# Import Settings model to ensure it's registered with Base
from model.settings import Settings
# Import AIAuditLog model to ensure it's registered with Base
from model.ai_audit_log import AIAuditLog

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kigate.db")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./kigate.db")

# Create async engine for FastAPI
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,  # Set to False in production
    future=True
)

# Create sync engine for admin operations
sync_engine = create_engine(
    DATABASE_URL,
    echo=True  # Set to False in production
)

# Session makers
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)


def migrate_database_schema(connection):
    """
    Migrate database schema to handle missing columns
    
    This function addresses the issue where existing databases may have been created 
    before new columns were added to models. Without this migration,
    SQLAlchemy would fail with "table has no column named X" errors.
    
    The migration is safe to run multiple times and on fresh databases.
    """
    import logging
    from sqlalchemy import text
    logger = logging.getLogger(__name__)
    
    try:
        # Check if jobs table exists
        inspector_result = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
        ).fetchone()
        
        if inspector_result:
            # Check if duration column exists in jobs table
            columns_result = connection.execute(text("PRAGMA table_info(jobs)")).fetchall()
            column_names = [col[1] for col in columns_result]  # col[1] is the column name
            
            if 'duration' not in column_names:
                logger.info("Database migration: Adding missing 'duration' column to jobs table")
                connection.execute(text("ALTER TABLE jobs ADD COLUMN duration INTEGER"))
                logger.info("Database migration: Successfully added 'duration' column to jobs table")
            
            if 'client_ip' not in column_names:
                logger.info("Database migration: Adding missing 'client_ip' column to jobs table")
                connection.execute(text("ALTER TABLE jobs ADD COLUMN client_ip VARCHAR(45)"))
                logger.info("Database migration: Successfully added 'client_ip' column to jobs table")
            
            if 'token_count' not in column_names:
                logger.info("Database migration: Adding missing 'token_count' column to jobs table")
                connection.execute(text("ALTER TABLE jobs ADD COLUMN token_count INTEGER"))
                logger.info("Database migration: Successfully added 'token_count' column to jobs table")
                
    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        # Don't raise the exception to avoid breaking the application startup
        # The column might be added by create_all if this is a fresh database


async def init_db():
    """Initialize the database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Run migrations to ensure schema is up to date
        await conn.run_sync(migrate_database_schema)


async def get_async_session() -> AsyncSession:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Get synchronous database session"""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


async def close_db():
    """Close database connections"""
    await async_engine.dispose()