"""
Job Statistics model for aggregated job data
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Integer, Float, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, ConfigDict
from model.user import Base


class JobStatistics(Base):
    """Job Statistics database model for aggregated job metrics"""
    __tablename__ = "job_statistics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Aggregation dimensions
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)  # day, week, month
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Grouping fields (one of these will be set depending on aggregation type)
    agent_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Aggregated metrics
    job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Average duration in ms
    
    # Metadata
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Create indexes for efficient querying
    __table_args__ = (
        Index('idx_period_type_start', 'period_type', 'period_start'),
        Index('idx_agent_name', 'agent_name'),
        Index('idx_provider', 'provider'),
        Index('idx_model', 'model'),
    )


# Pydantic models for API
class JobStatisticsResponse(BaseModel):
    """Model for job statistics response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    period_type: str
    period_start: datetime
    period_end: datetime
    agent_name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    job_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    avg_duration: Optional[float] = None
    calculated_at: datetime


class JobStatisticsSummary(BaseModel):
    """Aggregated summary for display"""
    model_config = ConfigDict(from_attributes=True)
    
    label: str  # Agent name, provider name, or model name
    job_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    avg_duration: Optional[float] = None
