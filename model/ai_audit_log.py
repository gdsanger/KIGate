"""
AI Audit Log model for tracking all API calls
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict
from model.user import Base


class AIAuditLog(Base):
    """AI Audit Log database model for tracking API calls"""
    __tablename__ = "ai_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    api_endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    client_secret: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Token/API key
    payload_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # First 500 chars
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(nullable=True)
    

# Pydantic models for API
class AIAuditLogCreate(BaseModel):
    """Model for creating an audit log entry"""
    client_ip: Optional[str] = None
    api_endpoint: str
    client_secret: Optional[str] = None
    payload_preview: Optional[str] = None
    user_id: Optional[str] = None
    status_code: Optional[int] = None


class AIAuditLogResponse(BaseModel):
    """Model for audit log response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    timestamp: datetime
    client_ip: Optional[str] = None
    api_endpoint: str
    client_secret: Optional[str] = None
    payload_preview: Optional[str] = None
    user_id: Optional[str] = None
    status_code: Optional[int] = None
