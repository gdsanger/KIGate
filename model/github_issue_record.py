"""
Database model for storing GitHub issue creation records
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from model.user import Base
from datetime import datetime, timezone

class GitHubIssueRecord(Base):
    """Database model for storing GitHub issue creation history"""
    __tablename__ = "github_issue_records"
    
    id = Column(Integer, primary_key=True, index=True)
    repository = Column(String(255), nullable=False, index=True)
    original_text = Column(Text, nullable=False)
    processed_text = Column(Text, nullable=True)  # AI-improved text
    issue_title = Column(String(255), nullable=True)
    issue_number = Column(Integer, nullable=True)
    issue_url = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=False)  # User who created the issue
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<GitHubIssueRecord(id={self.id}, repository={self.repository}, success={self.success})>"