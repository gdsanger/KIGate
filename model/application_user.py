"""
ApplicationUser model for KIGate Admin Panel users with SQLite support
This model represents users who can log into the admin panel
"""
import uuid
import bcrypt
import secrets
import string
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict, Field, EmailStr

from model.user import Base  # Import the existing Base


class ApplicationUser(Base):
    """ApplicationUser database model for admin panel authentication"""
    __tablename__ = "application_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)  # bcrypt hash
    last_logon: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def set_password(self, password: str) -> None:
        """Hash and set password using bcrypt"""
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def generate_secure_password(self) -> str:
        """Generate a secure password with minimum 10 characters"""
        # Use a combination of letters, digits, and special characters
        alphabet = string.ascii_letters + string.digits + "!@#$%&*"
        # Ensure at least one character from each category
        password_chars = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase), 
            secrets.choice(string.digits),
            secrets.choice("!@#$%&*")
        ]
        
        # Fill the rest to make it at least 10 characters
        for _ in range(6):
            password_chars.append(secrets.choice(alphabet))
        
        # Shuffle the characters
        secrets.SystemRandom().shuffle(password_chars)
        return ''.join(password_chars)
    
    def update_last_logon(self):
        """Update last logon timestamp"""
        from datetime import timezone
        self.last_logon = datetime.now(timezone.utc)


# Pydantic models for API
class ApplicationUserCreate(BaseModel):
    """Model for creating an ApplicationUser"""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr = Field(..., max_length=200)
    password: Optional[str] = Field(None, min_length=1)  # Optional - will generate if not provided
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class ApplicationUserUpdate(BaseModel):
    """Model for updating an ApplicationUser"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = Field(None, max_length=200)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationUserResponse(BaseModel):
    """Model for ApplicationUser response"""
    id: str
    name: str
    email: str
    last_logon: Optional[datetime]
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ApplicationUserPasswordChange(BaseModel):
    """Model for changing an ApplicationUser's password"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=256)
    
    model_config = ConfigDict(from_attributes=True)


class ApplicationUserWithPassword(ApplicationUserResponse):
    """Model for ApplicationUser response including password (for reset operations)"""
    generated_password: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)