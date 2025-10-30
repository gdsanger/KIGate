"""
Provider model for AI API configuration
"""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Boolean, DateTime, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, ConfigDict, Field

from model.user import Base


class Provider(Base):
    """Provider database model for AI API configuration"""
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, gemini, claude, ollama
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # For Ollama
    organization_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # For OpenAI
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to models
    models: Mapped[List["ProviderModel"]] = relationship("ProviderModel", back_populates="provider", cascade="all, delete-orphan")


class ProviderModel(Base):
    """Provider Model database model for managing available AI models"""
    __tablename__ = "provider_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("providers.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False)  # API identifier
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship to provider
    provider: Mapped["Provider"] = relationship("Provider", back_populates="models")


# Pydantic models for API
class ProviderCreate(BaseModel):
    """Model for creating a provider"""
    name: str = Field(..., min_length=1, max_length=100)
    provider_type: str = Field(..., pattern="^(openai|gemini|claude|ollama)$")
    api_key: Optional[str] = Field(None, max_length=500)
    api_url: Optional[str] = Field(None, max_length=500)
    organization_id: Optional[str] = Field(None, max_length=200)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class ProviderUpdate(BaseModel):
    """Model for updating a provider"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, max_length=500)
    api_url: Optional[str] = Field(None, max_length=500)
    organization_id: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class ProviderResponse(BaseModel):
    """Model for provider response"""
    id: str
    name: str
    provider_type: str
    api_key: Optional[str]
    api_url: Optional[str]
    organization_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ProviderModelCreate(BaseModel):
    """Model for creating a provider model"""
    provider_id: str
    model_name: str = Field(..., min_length=1, max_length=200)
    model_id: str = Field(..., min_length=1, max_length=200)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class ProviderModelUpdate(BaseModel):
    """Model for updating a provider model"""
    model_name: Optional[str] = Field(None, min_length=1, max_length=200)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class ProviderModelResponse(BaseModel):
    """Model for provider model response"""
    id: str
    provider_id: str
    model_name: str
    model_id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProviderWithModels(ProviderResponse):
    """Model for provider response including models"""
    models: List[ProviderModelResponse] = []

    model_config = ConfigDict(from_attributes=True)
