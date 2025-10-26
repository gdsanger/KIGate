"""
Models for PDF Agent Execution API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from fastapi import UploadFile


class PDFAgentExecutionRequest(BaseModel):
    """Request model for PDF agent execution"""
    agent_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=36)
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional key-value parameters for the agent")
    chunk_size: Optional[int] = Field(default=4000, description="Size of text chunks for processing")


class PDFAgentExecutionResponse(BaseModel):
    """Response model for PDF agent execution"""
    job_id: str
    agent: str
    provider: str
    model: str
    status: str
    result: str
    chunks_processed: int
    pdf_filename: str