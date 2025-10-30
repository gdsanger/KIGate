"""
Database model for storing GitHub repositories
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from model.user import Base
from datetime import datetime, timezone

class Repository(Base):
    """Database model for storing GitHub repositories"""
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, unique=True, index=True)  # owner/repo
    owner = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    html_url = Column(String(500), nullable=False)
    is_private = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)  # Whether to show in dropdown
    last_updated = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<Repository(id={self.id}, full_name={self.full_name}, is_active={self.is_active})>"


# Pydantic models for API
from pydantic import BaseModel, Field
from typing import Optional, List

class RepositoryCreate(BaseModel):
    """Model for creating a repository record"""
    full_name: str = Field(..., min_length=1, max_length=255)
    owner: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    html_url: str = Field(..., min_length=1, max_length=500)
    is_private: bool = False
    is_active: bool = True

class RepositoryUpdate(BaseModel):
    """Model for updating a repository record"""
    description: Optional[str] = None
    is_active: Optional[bool] = None

class RepositoryResponse(BaseModel):
    """Model for repository API response"""
    id: int
    full_name: str
    owner: str
    name: str
    description: Optional[str]
    html_url: str
    is_private: bool
    is_active: bool
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True