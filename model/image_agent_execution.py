"""
Models for Image Agent Execution API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ImageAgentExecutionRequest(BaseModel):
    """Request model for Image agent execution"""
    agent_name: str = Field(..., min_length=1, max_length=100)
    provider: Optional[str] = Field(default=None, min_length=1, max_length=50)
    model: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=36)
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional key-value parameters for the agent")


class ImageAgentExecutionResponse(BaseModel):
    """Response model for Image agent execution"""
    success: bool
    text: str
    agent: str
    provider: str
    model: str
    job_id: str
    image_filename: str
