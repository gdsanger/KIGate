"""
Models for DOCX Agent Execution API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from fastapi import UploadFile


class DocxAgentExecutionRequest(BaseModel):
    """Request model for DOCX agent execution"""
    agent_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=36)
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional key-value parameters for the agent")
    chunk_size: Optional[int] = Field(default=4000, description="Size of text chunks for processing")


class DocxAgentExecutionResponse(BaseModel):
    """Response model for DOCX agent execution"""
    job_id: str
    agent: str
    provider: str
    model: str
    status: str = Field(..., description="Job status: 'completed', 'failed', or 'partially_completed' (some chunks failed)")
    result: str
    chunks_processed: int
    docx_filename: str