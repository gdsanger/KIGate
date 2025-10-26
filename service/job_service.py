"""
Job Service for managing job operations
"""
import uuid
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from model.job import Job, JobCreate, JobResponse

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
                status=job_data.status or "created"
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
    async def get_jobs_paginated(cls, db: AsyncSession, page: int = 1, per_page: int = 25) -> tuple[List[JobResponse], int]:
        """Get jobs with pagination, ordered by created_at descending"""
        try:
            # Calculate offset
            offset = (page - 1) * per_page
            
            # Get total count
            count_result = await db.execute(select(func.count(Job.id)))
            total_count = count_result.scalar()
            
            # Get jobs for current page
            result = await db.execute(
                select(Job)
                .order_by(desc(Job.created_at))
                .limit(per_page)
                .offset(offset)
            )
            jobs = result.scalars().all()
            
            job_responses = [JobResponse.model_validate(job) for job in jobs]
            
            return job_responses, total_count
            
        except Exception as e:
            logger.error(f"Error getting paginated jobs: {str(e)}")
            return [], 0