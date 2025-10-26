"""
Authentication module for KIGate API
"""
from typing import Optional
from fastapi import HTTPException, Depends, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from service.user_service import UserService
from service.rate_limit_service import RateLimitService
from model.user import User

security = HTTPBearer()


async def authenticate_user_by_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Authenticate user by Bearer token (client_secret)
    Expected format: Bearer {client_id}:{client_secret}
    Also performs initial rate limit check (RPM only, TPM checked later with actual token usage)
    """
    token = credentials.credentials
    
    try:
        # Parse client_id:client_secret format
        if ':' not in token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format. Expected client_id:client_secret",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        client_id, client_secret = token.split(':', 1)
        
        user = await UserService.authenticate_user(db, client_id, client_secret)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials or inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check rate limits (RPM check)
        is_allowed, error_message = await RateLimitService.check_rate_limits(db, user)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message,
                headers={"Retry-After": "60"}
            )
        
        await db.commit()  # Commit the last_login update
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def authenticate_user_by_params(
    client_id: str,
    client_secret: str,
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Authenticate user by query parameters
    """
    user = await UserService.authenticate_user(db, client_id, client_secret)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or inactive user"
        )
    
    await db.commit()  # Commit the last_login update
    return user


# Dependency function factory for API key authentication
def get_current_user_by_api_key(api_key: str):
    """Factory function to create dependency for API key authentication"""
    async def _get_current_user(db: AsyncSession = Depends(get_async_session)) -> Optional[User]:
        """
        Authenticate user by api_key parameter (backward compatibility)
        Expects api_key in format: client_id:client_secret
        """
        if not api_key:
            return None
        
        try:
            if ':' in api_key:
                client_id, client_secret = api_key.split(':', 1)
                user = await UserService.authenticate_user(db, client_id, client_secret)
                if user:
                    await db.commit()  # Commit the last_login update
                return user
        except ValueError:
            pass
        
        return None
    
    return _get_current_user