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
# Import Provider and ProviderModel models to ensure they're registered with Base
from model.provider import Provider, ProviderModel
# Import Settings model to ensure it's registered with Base
from model.settings import Settings
# Import AIAuditLog model to ensure it's registered with Base
from model.ai_audit_log import AIAuditLog
# Import JobStatistics model to ensure it's registered with Base
from model.job_statistics import JobStatistics

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/kigate.db")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./data/kigate.db")

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
    SQLAlchemy would fail when trying to INSERT new records with missing columns.
    
    Also adds 'role' column to users and application_users tables if missing.
    
    The migration is safe to run multiple times and on fresh databases.
    """
    import logging
    from sqlalchemy import text
    logger = logging.getLogger(__name__)
    
    try:
        # Check if jobs table exists and add duration column if missing
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
            
            if 'output_token_count' not in column_names:
                logger.info("Database migration: Adding missing 'output_token_count' column to jobs table")
                connection.execute(text("ALTER TABLE jobs ADD COLUMN output_token_count INTEGER"))
                logger.info("Database migration: Successfully added 'output_token_count' column to jobs table")
            else:
                logger.debug("Database migration: 'duration' column already exists in jobs table")
        
        # Check if users table exists and add role column if missing
        # Check if users table exists and add rate limiting columns if missing
        users_result = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        ).fetchone()
        
        if users_result:
            columns_result = connection.execute(text("PRAGMA table_info(users)")).fetchall()
            column_names = [col[1] for col in columns_result]
            
            if 'role' not in column_names:
                logger.info("Database migration: Adding missing 'role' column to users table")
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL"))
                logger.info("Database migration: Successfully added 'role' column to users table")
            else:
                logger.debug("Database migration: 'role' column already exists in users table")
        
        # Check if application_users table exists and add role column if missing
        app_users_result = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='application_users'")
        ).fetchone()
        
        if app_users_result:
            columns_result = connection.execute(text("PRAGMA table_info(application_users)")).fetchall()
            column_names = [col[1] for col in columns_result]
            
            if 'role' not in column_names:
                logger.info("Database migration: Adding missing 'role' column to application_users table")
                connection.execute(text("ALTER TABLE application_users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL"))
                logger.info("Database migration: Successfully added 'role' column to application_users table")
            else:
                logger.debug("Database migration: 'role' column already exists in application_users table")
            # Check which columns exist in users table
            columns_result = connection.execute(text("PRAGMA table_info(users)")).fetchall()
            column_names = [col[1] for col in columns_result]  # col[1] is the column name
            
            # Add rpm_limit column if missing
            if 'rpm_limit' not in column_names:
                logger.info("Database migration: Adding missing 'rpm_limit' column to users table")
                connection.execute(text("ALTER TABLE users ADD COLUMN rpm_limit INTEGER NOT NULL DEFAULT 20"))
                logger.info("Database migration: Successfully added 'rpm_limit' column to users table")
            
            # Add tpm_limit column if missing
            if 'tpm_limit' not in column_names:
                logger.info("Database migration: Adding missing 'tpm_limit' column to users table")
                connection.execute(text("ALTER TABLE users ADD COLUMN tpm_limit INTEGER NOT NULL DEFAULT 50000"))
                logger.info("Database migration: Successfully added 'tpm_limit' column to users table")
            
            # Add current_rpm column if missing
            if 'current_rpm' not in column_names:
                logger.info("Database migration: Adding missing 'current_rpm' column to users table")
                connection.execute(text("ALTER TABLE users ADD COLUMN current_rpm INTEGER NOT NULL DEFAULT 0"))
                logger.info("Database migration: Successfully added 'current_rpm' column to users table")
            
            # Add current_tpm column if missing
            if 'current_tpm' not in column_names:
                logger.info("Database migration: Adding missing 'current_tpm' column to users table")
                connection.execute(text("ALTER TABLE users ADD COLUMN current_tpm INTEGER NOT NULL DEFAULT 0"))
                logger.info("Database migration: Successfully added 'current_tpm' column to users table")
            
            # Add last_reset_time column if missing
            if 'last_reset_time' not in column_names:
                logger.info("Database migration: Adding missing 'last_reset_time' column to users table")
                connection.execute(text("ALTER TABLE users ADD COLUMN last_reset_time DATETIME"))
                logger.info("Database migration: Successfully added 'last_reset_time' column to users table")
        
        # Check if provider_models table exists and add pricing columns if missing
        provider_models_result = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='provider_models'")
        ).fetchone()
        
        if provider_models_result:
            columns_result = connection.execute(text("PRAGMA table_info(provider_models)")).fetchall()
            column_names = [col[1] for col in columns_result]
            
            if 'input_price_per_million' not in column_names:
                logger.info("Database migration: Adding missing 'input_price_per_million' column to provider_models table")
                connection.execute(text("ALTER TABLE provider_models ADD COLUMN input_price_per_million FLOAT"))
                logger.info("Database migration: Successfully added 'input_price_per_million' column to provider_models table")
            
            if 'output_price_per_million' not in column_names:
                logger.info("Database migration: Adding missing 'output_price_per_million' column to provider_models table")
                connection.execute(text("ALTER TABLE provider_models ADD COLUMN output_price_per_million FLOAT"))
                logger.info("Database migration: Successfully added 'output_price_per_million' column to provider_models table")
                
    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        # Don't raise the exception to avoid breaking the application startup
        # The columns might be added by create_all if this is a fresh database


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