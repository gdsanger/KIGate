"""
AI Agent Generator models for generating agents via AI
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AgentGenerationRequest(BaseModel):
    """Request model for AI-powered agent generation"""
    description: str = Field(..., min_length=10, max_length=2000, description="User description of what the agent should do")


class AgentGenerationResponse(BaseModel):
    """Response model for AI-powered agent generation"""
    name: str = Field(..., description="Generated agent name")
    description: str = Field(..., description="Generated agent description")
    role: str = Field(..., description="Generated agent role")
    provider: str = Field(..., description="Recommended AI provider")
    model: str = Field(..., description="Recommended AI model")
    task: str = Field(..., description="Generated detailed task prompt")
    parameters: Optional[List[Dict[str, Any]]] = Field(default=None, description="Generated parameters")
    confidence_score: Optional[float] = Field(default=None, description="AI confidence in the generation (0-1)")


class AgentGenerationReview(BaseModel):
    """Model for reviewing generated agent before creation"""
    name: str = Field(...)
    description: str = Field(...)
    role: str = Field(...)
    provider: str = Field(...)
    model: str = Field(...)
    task: str = Field(...)
    parameters: Optional[str] = Field(default=None, description="Parameters as YAML string")
    user_description: str = Field(..., description="Original user description for regeneration")
    accepted: bool = Field(..., description="Whether the user accepted the generated agent")