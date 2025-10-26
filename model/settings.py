"""
Settings model for KIGate API configuration
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict
from model.user import Base


class Settings(Base):
    """Settings database model for application configuration"""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )


# Pydantic models for API
class SettingsCreate(BaseModel):
    """Model for creating a setting"""
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    is_secret: bool = False


class SettingsUpdate(BaseModel):
    """Model for updating a setting"""
    value: Optional[str] = None
    description: Optional[str] = None
    is_secret: Optional[bool] = None


class SettingsResponse(BaseModel):
    """Model for settings response"""
    model_config = ConfigDict(from_attributes=True)
    
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    is_secret: bool
    updated_at: datetime
