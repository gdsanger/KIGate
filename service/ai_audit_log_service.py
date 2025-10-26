"""
AI Audit Log service for KIGate API
"""
import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from model.ai_audit_log import AIAuditLog, AIAuditLogCreate

logger = logging.getLogger(__name__)


class AIAuditLogService:
    """Service for managing AI API audit logs"""
    
    @staticmethod
    async def create_log(db: AsyncSession, log_data: AIAuditLogCreate) -> AIAuditLog:
        """Create a new audit log entry"""
        audit_log = AIAuditLog(
            client_ip=log_data.client_ip,
            api_endpoint=log_data.api_endpoint,
            client_secret=log_data.client_secret,
            payload_preview=log_data.payload_preview,
            user_id=log_data.user_id,
            status_code=log_data.status_code
        )
        db.add(audit_log)
        await db.flush()
        return audit_log
    
    @staticmethod
    async def get_logs_paginated(db: AsyncSession, page: int = 1, per_page: int = 50) -> Tuple[List[AIAuditLog], int]:
        """Get audit logs with pagination"""
        offset = (page - 1) * per_page
        
        # Get logs
        result = await db.execute(
            select(AIAuditLog)
            .order_by(desc(AIAuditLog.timestamp))
            .limit(per_page)
            .offset(offset)
        )
        logs = list(result.scalars().all())
        
        # Get total count
        count_result = await db.execute(select(func.count(AIAuditLog.id)))
        total_count = count_result.scalar()
        
        return logs, total_count
    
    @staticmethod
    async def get_logs_by_user(db: AsyncSession, user_id: str, limit: int = 100) -> List[AIAuditLog]:
        """Get audit logs for a specific user"""
        result = await db.execute(
            select(AIAuditLog)
            .where(AIAuditLog.user_id == user_id)
            .order_by(desc(AIAuditLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_logs_by_endpoint(db: AsyncSession, endpoint: str, limit: int = 100) -> List[AIAuditLog]:
        """Get audit logs for a specific endpoint"""
        result = await db.execute(
            select(AIAuditLog)
            .where(AIAuditLog.api_endpoint == endpoint)
            .order_by(desc(AIAuditLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    def truncate_payload(payload: str, max_length: int = 500) -> str:
        """Truncate payload to specified length"""
        if not payload:
            return ""
        if len(payload) <= max_length:
            return payload
        return payload[:max_length] + "..."
    
    @staticmethod
    def mask_secret(secret: Optional[str]) -> Optional[str]:
        """Mask sensitive parts of client secret/token"""
        if not secret:
            return None
        if len(secret) <= 8:
            return "*" * len(secret)
        # Show first 4 and last 4 characters
        return f"{secret[:4]}...{secret[-4:]}"
