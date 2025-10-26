"""
Job model for KIGate API with SQLite support
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict
from model.user import Base


class Job(Base):
    """Job database model"""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


# Pydantic models for API
class JobCreate(BaseModel):
    """Model for creating a job"""
    name: str
    user_id: str
    provider: str
    model: str
    status: str = "created"
    client_ip: Optional[str] = None
    token_count: Optional[int] = None


class JobResponse(BaseModel):
    """Model for job response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    user_id: str
    provider: str
    model: str
    status: str
    created_at: datetime
    duration: Optional[int] = None
    client_ip: Optional[str] = None
    token_count: Optional[int] = None