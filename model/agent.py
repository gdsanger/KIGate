"""
Agent model for KIGate API
"""
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field


class Agent(BaseModel):
    """Agent model for YAML configuration"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    role: str = Field(..., min_length=1, max_length=200)
    provider: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=100)
    task: str = Field(..., min_length=1)
    parameters: Optional[List[Dict[str, Any]]] = Field(default=None)


class AgentCreate(BaseModel):
    """Model for creating an agent"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    role: str = Field(..., min_length=1, max_length=200)
    provider: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=100)
    task: str = Field(..., min_length=1)
    parameters: Optional[List[Dict[str, Any]]] = Field(default=None)


class AgentUpdate(BaseModel):
    """Model for updating an agent"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    role: Optional[str] = Field(None, min_length=1, max_length=200)
    provider: Optional[str] = Field(None, min_length=1, max_length=50)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    task: Optional[str] = Field(None, min_length=1)
    parameters: Optional[List[Dict[str, Any]]] = Field(default=None)