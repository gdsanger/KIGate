"""
Models for Agent Execution API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class AgentExecutionRequest(BaseModel):
    """Request model for agent execution"""
    agent_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1, max_length=36)
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional key-value parameters for the agent")
    use_cache: bool = Field(default=True, description="Enable/disable caching")
    force_refresh: bool = Field(default=False, description="Force cache refresh, ignore existing cache")
    cache_ttl: Optional[int] = Field(default=None, description="Custom TTL in seconds for cache entry")


class CacheMetadata(BaseModel):
    """Cache metadata model"""
    status: str = Field(..., description="Cache status: hit, miss, or bypassed")
    cached_at: Optional[str] = Field(default=None, description="Timestamp when result was cached")
    ttl: Optional[int] = Field(default=None, description="TTL in seconds")


class AgentExecutionResponse(BaseModel):
    """Response model for agent execution"""
    job_id: str
    agent: str
    provider: str
    model: str
    status: str
    result: str
    cache: Optional[CacheMetadata] = Field(default=None, description="Cache metadata")