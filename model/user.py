"""
User model for KIGate API with SQLite support
"""
import uuid
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, Integer, func
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
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Rate limiting fields
    rpm_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)  # Requests per minute
    tpm_limit: Mapped[int] = mapped_column(Integer, default=50000, nullable=False)  # Tokens per minute
    current_rpm: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Current requests this minute
    current_tpm: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Current tokens this minute
    last_reset_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    
    def reset_rate_limits_if_needed(self):
        """Reset rate limit counters if more than 1 minute has passed"""
        now = datetime.utcnow()
        if self.last_reset_time is None or (now - self.last_reset_time).total_seconds() >= 60:
            self.current_rpm = 0
            self.current_tpm = 0
            self.last_reset_time = now
    
    def check_rpm_limit(self) -> bool:
        """Check if user has exceeded RPM limit. Returns True if within limit."""
        self.reset_rate_limits_if_needed()
        return self.current_rpm < self.rpm_limit
    
    def check_tpm_limit(self, tokens: int) -> bool:
        """Check if adding tokens would exceed TPM limit. Returns True if within limit."""
        self.reset_rate_limits_if_needed()
        return (self.current_tpm + tokens) <= self.tpm_limit
    
    def increment_request_count(self):
        """Increment the request counter"""
        self.reset_rate_limits_if_needed()
        self.current_rpm += 1
    
    def add_token_usage(self, tokens: int):
        """Add token usage to the counter"""
        self.reset_rate_limits_if_needed()
        self.current_tpm += tokens


# Pydantic models for API
class UserCreate(BaseModel):
    """Model for creating a user"""
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=200)
    role: str = Field(default="user", pattern="^(admin|user)$")
    is_active: bool = True
    rpm_limit: int = Field(default=20, ge=1)
    tpm_limit: int = Field(default=50000, ge=1)

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Model for updating a user"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None
    rpm_limit: Optional[int] = Field(None, ge=1)
    tpm_limit: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Model for user response"""
    client_id: str
    name: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    rpm_limit: int
    tpm_limit: int
    current_rpm: int
    current_tpm: int
    last_reset_time: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UserWithSecret(UserResponse):
    """Model for user response including client secret (admin only)"""
    client_secret: str

    model_config = ConfigDict(from_attributes=True)