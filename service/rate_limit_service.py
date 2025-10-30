"""
Rate limiting service for KIGate API
Handles RPM (Requests Per Minute) and TPM (Tokens Per Minute) enforcement
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from model.user import User

logger = logging.getLogger(__name__)


class RateLimitService:
    """Service for rate limit management and enforcement"""
    
    @staticmethod
    async def check_rate_limits(db: AsyncSession, user: User, estimated_tokens: int = 0) -> tuple[bool, Optional[str]]:
        """
        Check if user is within rate limits before processing request
        
        Args:
            db: Database session
            user: The user to check limits for
            estimated_tokens: Estimated tokens for the request (0 means skip TPM check)
            
        Returns:
            Tuple of (is_allowed, error_message)
            - (True, None) if within limits
            - (False, error_message) if limits exceeded
        """
        # Reset counters if needed
        user.reset_rate_limits_if_needed()
        
        # Check RPM limit
        if not user.check_rpm_limit():
            logger.warning(f"User {user.client_id} exceeded RPM limit: {user.current_rpm}/{user.rpm_limit}")
            return False, f"Rate limit exceeded: {user.current_rpm}/{user.rpm_limit} requests per minute"
        
        # Check TPM limit if tokens are provided
        if estimated_tokens > 0 and not user.check_tpm_limit(estimated_tokens):
            logger.warning(f"User {user.client_id} would exceed TPM limit: {user.current_tpm + estimated_tokens}/{user.tpm_limit}")
            return False, f"Token limit exceeded: would use {user.current_tpm + estimated_tokens}/{user.tpm_limit} tokens per minute"
        
        return True, None
    
    @staticmethod
    async def record_request(db: AsyncSession, user: User, tokens_used: int = 0):
        """
        Record a request and token usage for rate limiting
        
        Args:
            db: Database session
            user: The user making the request
            tokens_used: Number of tokens used in the request
        """
        # Increment request counter
        user.increment_request_count()
        
        # Add token usage
        if tokens_used > 0:
            user.add_token_usage(tokens_used)
        
        # Flush changes to database
        await db.flush()
        
        logger.debug(f"User {user.client_id} - RPM: {user.current_rpm}/{user.rpm_limit}, TPM: {user.current_tpm}/{user.tpm_limit}")
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count from text
        Rough approximation: 1 token ≈ 4 characters
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        # Conservative estimate: 1 token per 3.5 characters on average
        return max(1, len(text) // 4)
