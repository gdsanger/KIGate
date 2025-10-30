"""
ApplicationUser service for managing admin panel user operations
"""
import uuid
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from model.application_user import (
    ApplicationUser, 
    ApplicationUserCreate, 
    ApplicationUserUpdate, 
    ApplicationUserPasswordChange,
    ApplicationUserResponse,
    ApplicationUserWithPassword
)
from service.graph_service import get_graph_service

logger = logging.getLogger(__name__)


class ApplicationUserService:
    """Service for ApplicationUser management operations"""
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: ApplicationUserCreate, send_email: bool = True) -> ApplicationUserWithPassword:
        """Create a new application user"""
        try:
            # Check if email already exists
            existing_user = await ApplicationUserService.get_user_by_email(db, user_data.email)
            if existing_user:
                raise ValueError("Email bereits vergeben")
            
            # Generate user ID
            user_id = str(uuid.uuid4())
            
            db_user = ApplicationUser(
                id=user_id,
                name=user_data.name,
                email=user_data.email,
                role=user_data.role,
                is_active=user_data.is_active
            )
            
            # Set password - generate if not provided
            if user_data.password:
                password = user_data.password
                db_user.set_password(password)
            else:
                password = db_user.generate_secure_password()
                db_user.set_password(password)
            
            db.add(db_user)
            await db.flush()
            await db.refresh(db_user)
            
            # Send email notification with credentials
            if send_email:
                try:
                    graph_service = get_graph_service()
                    email_sent = await graph_service.send_admin_user_credentials_email(
                        user_name=user_data.name,
                        user_email=user_data.email,
                        username=user_data.email,  # Email is used as username
                        password=password
                    )
                    
                    if email_sent:
                        logger.info(f"Admin user credentials email sent successfully to {user_data.email}")
                    else:
                        logger.warning(f"Failed to send admin user credentials email to {user_data.email}")
                except Exception as e:
                    logger.error(f"Error sending admin user credentials email: {e}")
                    # Don't fail user creation if email fails
            
            # Create response with generated password
            response = ApplicationUserWithPassword.model_validate(db_user)
            response.generated_password = password
            return response
            
        except IntegrityError:
            await db.rollback()
            raise ValueError("Email bereits vergeben")
    
    @staticmethod
    async def get_user(db: AsyncSession, user_id: str) -> Optional[ApplicationUserResponse]:
        """Get user by ID"""
        result = await db.execute(select(ApplicationUser).where(ApplicationUser.id == user_id))
        user = result.scalar_one_or_none()
        
        if user:
            return ApplicationUserResponse.model_validate(user)
        return None
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[ApplicationUserResponse]:
        """Get user by email"""
        result = await db.execute(select(ApplicationUser).where(ApplicationUser.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            return ApplicationUserResponse.model_validate(user)
        return None
    
    @staticmethod
    async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ApplicationUserResponse]:
        """Get all users with pagination"""
        result = await db.execute(
            select(ApplicationUser).offset(skip).limit(limit).order_by(ApplicationUser.created_at.desc())
        )
        users = result.scalars().all()
        
        return [ApplicationUserResponse.model_validate(user) for user in users]
    
    @staticmethod
    async def update_user(db: AsyncSession, user_id: str, user_data: ApplicationUserUpdate) -> Optional[ApplicationUserResponse]:
        """Update user information"""
        try:
            result = await db.execute(select(ApplicationUser).where(ApplicationUser.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Check email uniqueness if email is being updated
            if user_data.email and user_data.email != user.email:
                existing_user = await ApplicationUserService.get_user_by_email(db, user_data.email)
                if existing_user:
                    raise ValueError("Email bereits vergeben")
            
            # Update only provided fields
            update_data = user_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)
            
            await db.flush()
            await db.refresh(user)
            
            return ApplicationUserResponse.model_validate(user)
            
        except IntegrityError:
            await db.rollback()
            raise ValueError("Email bereits vergeben")
    
    @staticmethod
    async def delete_user(db: AsyncSession, user_id: str) -> bool:
        """Delete user by ID"""
        result = await db.execute(select(ApplicationUser).where(ApplicationUser.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        await db.delete(user)
        return True
    
    @staticmethod
    async def toggle_user_status(db: AsyncSession, user_id: str) -> Optional[ApplicationUserResponse]:
        """Toggle user active status"""
        result = await db.execute(select(ApplicationUser).where(ApplicationUser.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        user.is_active = not user.is_active
        await db.flush()
        await db.refresh(user)
        
        return ApplicationUserResponse.model_validate(user)
    
    @staticmethod
    async def reset_password(db: AsyncSession, user_id: str, send_email: bool = True) -> Optional[ApplicationUserWithPassword]:
        """Reset user password and optionally send email"""
        result = await db.execute(select(ApplicationUser).where(ApplicationUser.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Generate new secure password
        new_password = user.generate_secure_password()
        user.set_password(new_password)
        
        await db.flush()
        await db.refresh(user)
        
        # Send email notification with new credentials
        if send_email:
            try:
                graph_service = get_graph_service()
                email_sent = await graph_service.send_admin_password_reset_email(
                    user_name=user.name,
                    user_email=user.email,
                    username=user.email,  # Email is used as username
                    new_password=new_password
                )
                
                if email_sent:
                    logger.info(f"Password reset email sent successfully to {user.email}")
                else:
                    logger.warning(f"Failed to send password reset email to {user.email}")
            except Exception as e:
                logger.error(f"Error sending password reset email: {e}")
                # Don't fail password reset if email fails
        
        # Create response with new password
        response = ApplicationUserWithPassword.model_validate(user)
        response.generated_password = new_password
        return response
    
    @staticmethod
    async def change_password(db: AsyncSession, user_id: str, current_password: str, new_password: str) -> Optional[ApplicationUserResponse]:
        """Change user password after verifying current password"""
        result = await db.execute(select(ApplicationUser).where(ApplicationUser.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Verify current password
        if not user.verify_password(current_password):
            raise ValueError("Aktuelles Passwort ist nicht korrekt")
        
        # Set new password
        user.set_password(new_password)
        
        await db.flush()
        await db.refresh(user)
        
        return ApplicationUserResponse.model_validate(user)
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[ApplicationUser]:
        """Authenticate user with email and password"""
        result = await db.execute(
            select(ApplicationUser).where(
                ApplicationUser.email == email,
                ApplicationUser.is_active
            )
        )
        user = result.scalar_one_or_none()
        
        if user and user.verify_password(password):
            # Update last logon
            user.update_last_logon()
            await db.flush()
            return user
        
        return None