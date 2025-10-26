"""
User service for managing user operations
"""
import uuid
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from model.user import User, UserCreate, UserUpdate, UserResponse, UserWithSecret
from service.graph_service import get_graph_service

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations"""
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate, send_email: bool = True) -> UserWithSecret:
        """Create a new user"""
        # Generate client_id and client_secret
        client_id = str(uuid.uuid4())
        
        db_user = User(
            client_id=client_id,
            name=user_data.name,
            email=user_data.email,
            role=user_data.role,
            is_active=user_data.is_active
        )
        
        # Generate client secret
        client_secret = db_user.generate_client_secret()
        
        db.add(db_user)
        await db.flush()
        await db.refresh(db_user)
        
        # Send email notification if user has email and send_email is True
        if send_email and user_data.email:
            try:
                graph_service = get_graph_service()
                email_sent = await graph_service.send_new_user_credentials_email(
                    user_name=user_data.name,
                    user_email=user_data.email,
                    client_id=client_id,
                    client_secret=client_secret
                )
                
                if email_sent:
                    logger.info(f"Welcome email sent successfully to {user_data.email}")
                else:
                    logger.warning(f"Failed to send welcome email to {user_data.email}")
            except Exception as e:
                logger.error(f"Error sending welcome email: {e}")
                # Don't fail user creation if email fails
        
        return UserWithSecret.model_validate(db_user)
    
    @staticmethod
    async def get_user(db: AsyncSession, client_id: str) -> Optional[UserResponse]:
        """Get user by client_id"""
        result = await db.execute(select(User).where(User.client_id == client_id))
        user = result.scalar_one_or_none()
        
        if user:
            return UserResponse.model_validate(user)
        return None
    
    @staticmethod
    async def get_user_with_secret(db: AsyncSession, client_id: str) -> Optional[UserWithSecret]:
        """Get user with secret by client_id (admin only)"""
        result = await db.execute(select(User).where(User.client_id == client_id))
        user = result.scalar_one_or_none()
        
        if user:
            return UserWithSecret.model_validate(user)
        return None
    
    @staticmethod
    async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """Get all users with pagination"""
        result = await db.execute(
            select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        
        return [UserResponse.model_validate(user) for user in users]
    
    @staticmethod
    async def get_users_with_secrets(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[UserWithSecret]:
        """Get all users with secrets for admin use"""
        result = await db.execute(
            select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        
        return [UserWithSecret.model_validate(user) for user in users]
    
    @staticmethod
    async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """Get all users - alias for get_users"""
        return await UserService.get_users(db, skip, limit)
    
    @staticmethod
    async def update_user(db: AsyncSession, client_id: str, user_data: UserUpdate) -> Optional[UserResponse]:
        """Update user information"""
        result = await db.execute(select(User).where(User.client_id == client_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Update only provided fields
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.flush()
        await db.refresh(user)
        
        return UserResponse.model_validate(user)
    
    @staticmethod
    async def delete_user(db: AsyncSession, client_id: str) -> bool:
        """Delete user by client_id"""
        result = await db.execute(select(User).where(User.client_id == client_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        await db.delete(user)
        return True
    
    @staticmethod
    async def regenerate_client_secret(db: AsyncSession, client_id: str, send_email: bool = True) -> Optional[str]:
        """Regenerate client secret for a user"""
        result = await db.execute(select(User).where(User.client_id == client_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        new_secret = user.generate_client_secret()
        await db.flush()
        
        # Send email notification if user has email and send_email is True
        if send_email and user.email:
            try:
                graph_service = get_graph_service()
                email_sent = await graph_service.send_secret_regenerated_email(
                    user_name=user.name,
                    user_email=user.email,
                    client_id=client_id,
                    new_client_secret=new_secret
                )
                
                if email_sent:
                    logger.info(f"Secret regeneration email sent successfully to {user.email}")
                else:
                    logger.warning(f"Failed to send secret regeneration email to {user.email}")
            except Exception as e:
                logger.error(f"Error sending secret regeneration email: {e}")
                # Don't fail secret regeneration if email fails
        
        return new_secret
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, client_id: str, client_secret: str) -> Optional[User]:
        """Authenticate user with client_id and client_secret"""
        result = await db.execute(
            select(User).where(
                User.client_id == client_id,
                User.is_active == True
            )
        )
        user = result.scalar_one_or_none()
        
        if user and user.verify_secret(client_secret):
            # Update last login
            user.update_last_login()
            await db.flush()
            return user
        
        return None
    
    @staticmethod
    async def toggle_user_status(db: AsyncSession, client_id: str) -> Optional[UserResponse]:
        """Toggle user active status"""
        result = await db.execute(select(User).where(User.client_id == client_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        user.is_active = not user.is_active
        await db.flush()
        await db.refresh(user)
        
        return UserResponse.model_validate(user)