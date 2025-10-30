"""
Settings service for KIGate API
"""
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from model.settings import Settings, SettingsCreate, SettingsUpdate, SettingsResponse

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing application settings"""
    
    @staticmethod
    async def get_setting(db: AsyncSession, key: str) -> Optional[Settings]:
        """Get a setting by key"""
        result = await db.execute(select(Settings).where(Settings.key == key))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_setting_value(db: AsyncSession, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get setting value by key, return default if not found"""
        setting = await SettingsService.get_setting(db, key)
        return setting.value if setting else default
    
    @staticmethod
    async def get_all_settings(db: AsyncSession) -> List[Settings]:
        """Get all settings"""
        result = await db.execute(select(Settings).order_by(Settings.key))
        return list(result.scalars().all())
    
    @staticmethod
    async def create_setting(db: AsyncSession, setting_data: SettingsCreate) -> Settings:
        """Create a new setting"""
        # Check if setting already exists
        existing = await SettingsService.get_setting(db, setting_data.key)
        if existing:
            raise ValueError(f"Setting with key '{setting_data.key}' already exists")
        
        setting = Settings(
            key=setting_data.key,
            value=setting_data.value,
            description=setting_data.description,
            is_secret=setting_data.is_secret
        )
        db.add(setting)
        await db.flush()
        return setting
    
    @staticmethod
    async def update_setting(db: AsyncSession, key: str, setting_data: SettingsUpdate) -> Optional[Settings]:
        """Update an existing setting"""
        setting = await SettingsService.get_setting(db, key)
        if not setting:
            return None
        
        if setting_data.value is not None:
            setting.value = setting_data.value
        if setting_data.description is not None:
            setting.description = setting_data.description
        if setting_data.is_secret is not None:
            setting.is_secret = setting_data.is_secret
        
        await db.flush()
        return setting
    
    @staticmethod
    async def upsert_setting(db: AsyncSession, key: str, value: Optional[str], 
                            description: Optional[str] = None, is_secret: bool = False) -> Settings:
        """Create or update a setting"""
        setting = await SettingsService.get_setting(db, key)
        if setting:
            setting.value = value
            if description is not None:
                setting.description = description
            setting.is_secret = is_secret
        else:
            setting = Settings(
                key=key,
                value=value,
                description=description,
                is_secret=is_secret
            )
            db.add(setting)
        
        await db.flush()
        return setting
    
    @staticmethod
    async def delete_setting(db: AsyncSession, key: str) -> bool:
        """Delete a setting"""
        setting = await SettingsService.get_setting(db, key)
        if not setting:
            return False
        
        await db.delete(setting)
        await db.flush()
        return True
    
    @staticmethod
    async def initialize_default_settings(db: AsyncSession):
        """Initialize default settings if they don't exist"""
        defaults = [
            {
                "key": "sentry_dsn",
                "value": "",
                "description": "Sentry DSN for error tracking",
                "is_secret": True
            },
            {
                "key": "sentry_environment",
                "value": "production",
                "description": "Sentry environment (production, staging, development)",
                "is_secret": False
            },
            {
                "key": "sentry_traces_sample_rate",
                "value": "0.1",
                "description": "Sentry traces sample rate (0.0 to 1.0)",
                "is_secret": False
            }
        ]
        
        for default in defaults:
            existing = await SettingsService.get_setting(db, default["key"])
            if not existing:
                setting = Settings(**default)
                db.add(setting)
        
        await db.flush()
        logger.info("Default settings initialized")
