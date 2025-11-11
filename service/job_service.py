"""
Job Service for managing job operations
"""
import uuid
import logging
from typing import Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, delete, and_
from sqlalchemy.orm import aliased
from model.job import Job, JobCreate, JobResponse
from model.user import User

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing jobs"""
    
    @classmethod
    async def create_job(cls, db: AsyncSession, job_data: JobCreate) -> JobResponse:
        """Create a new job"""
        try:
            # Generate unique ID and name if not provided
            job_id = str(uuid.uuid4())
            job_name = job_data.name if hasattr(job_data, 'name') and job_data.name else f"job-{job_id[:8]}"
            
            db_job = Job(
                id=job_id,
                name=job_name,
                user_id=job_data.user_id,
                provider=job_data.provider,
                model=job_data.model,
                status=job_data.status or "created",
                client_ip=job_data.client_ip if hasattr(job_data, 'client_ip') else None,
                token_count=job_data.token_count if hasattr(job_data, 'token_count') else None,
                output_token_count=job_data.output_token_count if hasattr(job_data, 'output_token_count') else None
            )
            
            db.add(db_job)
            await db.flush()  # Ensure the job gets an ID
            await db.refresh(db_job)
            
            logger.info(f"Created job {job_id} for user {job_data.user_id}")
            
            return JobResponse.model_validate(db_job)
            
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            raise
    
    @classmethod
    async def get_job_by_id(cls, db: AsyncSession, job_id: str) -> Optional[JobResponse]:
        """Get a job by ID"""
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if job:
                return JobResponse.model_validate(job)
            return None
            
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {str(e)}")
            return None
    
    @classmethod
    async def update_job_status(cls, db: AsyncSession, job_id: str, status: str) -> bool:
        """Update job status"""
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if job:
                job.status = status
                await db.flush()
                logger.info(f"Updated job {job_id} status to {status}")
                return True
            
            logger.warning(f"Job {job_id} not found for status update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating job {job_id} status: {str(e)}")
            return False
    
    @classmethod
    async def update_job_duration(cls, db: AsyncSession, job_id: str, duration: int) -> bool:
        """Update job duration in milliseconds"""
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if job:
                job.duration = duration
                await db.flush()
                logger.info(f"Updated job {job_id} duration to {duration}ms")
                return True
            
            logger.warning(f"Job {job_id} not found for duration update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating job {job_id} duration: {str(e)}")
            return False
    
    @classmethod
    async def update_job_token_count(cls, db: AsyncSession, job_id: str, token_count: int) -> bool:
        """Update job token count"""
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if job:
                job.token_count = token_count
                await db.flush()
                logger.info(f"Updated job {job_id} token count to {token_count}")
                return True
            
            logger.warning(f"Job {job_id} not found for token count update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating job {job_id} token count: {str(e)}")
            return False
    
    @classmethod
    async def update_job_output_token_count(cls, db: AsyncSession, job_id: str, output_token_count: int) -> bool:
        """Update job output token count"""
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if job:
                job.output_token_count = output_token_count
                await db.flush()
                logger.info(f"Updated job {job_id} output token count to {output_token_count}")
                return True
            
            logger.warning(f"Job {job_id} not found for output token count update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating job {job_id} output token count: {str(e)}")
            return False

    @classmethod
    async def get_jobs_paginated(
        cls, 
        db: AsyncSession, 
        page: int = 1, 
        per_page: int = 25,
        status_filter: Optional[str] = None,
        provider_filter: Optional[str] = None,
        name_filter: Optional[str] = None
    ) -> Tuple[List[dict], int]:
        """Get jobs with pagination and optional filters, ordered by created_at descending
        Returns jobs with user names instead of just user_id"""
        try:
            # Calculate offset
            offset = (page - 1) * per_page
            
            # Use aliased User table for clarity
            UserAlias = aliased(User)
            
            # Build base query with user join
            query = select(Job, UserAlias.name.label('user_name')).outerjoin(
                UserAlias, Job.user_id == UserAlias.client_id
            )
            count_query = select(func.count(Job.id))
            
            # Apply filters
            filters = []
            if status_filter:
                filters.append(Job.status == status_filter)
            if provider_filter:
                filters.append(Job.provider == provider_filter)
            if name_filter:
                filters.append(Job.name.ilike(f"%{name_filter}%"))
            
            if filters:
                filter_condition = and_(*filters)
                query = query.where(filter_condition)
                count_query = count_query.where(filter_condition)
            
            # Get total count
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()
            
            # Get jobs for current page
            result = await db.execute(
                query
                .order_by(desc(Job.created_at))
                .limit(per_page)
                .offset(offset)
            )
            rows = result.all()
            
            # Convert to dict with user_name
            job_list = []
            for job, user_name in rows:
                job_dict = {
                    'id': job.id,
                    'name': job.name,
                    'user_id': job.user_id,
                    'user_name': user_name or 'Unbekannt',
                    'provider': job.provider,
                    'model': job.model,
                    'status': job.status,
                    'created_at': job.created_at,
                    'duration': job.duration,
                    'client_ip': job.client_ip,
                    'token_count': job.token_count,
                    'output_token_count': job.output_token_count
                }
                job_list.append(job_dict)
            
            return job_list, total_count
            
        except Exception as e:
            logger.error(f"Error getting paginated jobs: {str(e)}")
            return [], 0

    @classmethod
    async def delete_old_jobs(cls, db: AsyncSession, days: int = 7) -> int:
        """Delete jobs older than specified days. Returns count of deleted jobs."""
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Count jobs to be deleted
            count_result = await db.execute(
                select(func.count(Job.id)).where(Job.created_at < cutoff_date)
            )
            count_to_delete = count_result.scalar()
            
            # Delete jobs older than cutoff date
            await db.execute(
                delete(Job).where(Job.created_at < cutoff_date)
            )
            
            logger.info(f"Deleted {count_to_delete} jobs older than {days} days")
            
            return count_to_delete
            
        except Exception as e:
            logger.error(f"Error deleting old jobs: {str(e)}")
            raise