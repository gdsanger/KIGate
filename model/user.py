"""
User model for KIGate API with SQLite support
"""
import uuid
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict, Field

Base = declarative_base()


class User(Base):
    """User database model"""
    __tablename__ = "users"

    client_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_secret: Mapped[str] = mapped_column(String(256), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def generate_client_secret(self) -> str:
        """Generate a new 128-bit client secret"""
        # Generate 128 bits (16 bytes) as hex string
        secret = secrets.token_hex(16)
        self.client_secret = secret
        return secret
    
    def verify_secret(self, secret: str) -> bool:
        """Verify client secret"""
        return self.client_secret == secret
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()


# Pydantic models for API
class UserCreate(BaseModel):
    """Model for creating a user"""
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=200)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Model for updating a user"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Model for user response"""
    client_id: str
    name: str
    email: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UserWithSecret(UserResponse):
    """Model for user response including client secret (admin only)"""
    client_secret: str

    model_config = ConfigDict(from_attributes=True)