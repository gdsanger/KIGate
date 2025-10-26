from pydantic import BaseModel
from typing import Optional
from enum import Enum

class IssueType(str, Enum):
    """GitHub issue types"""
    BUG = "bug"
    FEATURE = "enhancement" 
    TASK = "task"

class GitHubIssueRequest(BaseModel):
    """Request model for creating GitHub issues"""
    repository: str  # Format: "owner/repo"
    text: str
    
class GitHubIssueResponse(BaseModel):
    """Response model for GitHub issue creation"""
    issue_number: int
    title: str
    issue_url: str
    success: bool
    error_message: Optional[str] = None

class ProcessedIssueContent(BaseModel):
    """Internal model for AI-processed issue content"""
    improved_text: str
    title: str
    issue_type: IssueType
    labels: list[str] = []