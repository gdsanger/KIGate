"""
Job Statistics Service for calculating and managing job statistics
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_, or_
from model.job import Job
from model.job_statistics import JobStatistics, JobStatisticsSummary
from model.provider import ProviderModel

logger = logging.getLogger(__name__)


class JobStatisticsService:
    """Service for calculating and managing job statistics"""
    
    @classmethod
    async def _get_model_pricing(cls, db: AsyncSession) -> Dict[str, Dict[str, float]]:
        """Get pricing information for all models"""
        provider_models_result = await db.execute(
            select(ProviderModel).where(
                ProviderModel.input_price_per_million.isnot(None),
                ProviderModel.output_price_per_million.isnot(None)
            )
        )
        provider_models = provider_models_result.scalars().all()
        
        model_pricing = {}
        for pm in provider_models:
            model_pricing[pm.model_id] = {
                'input_price': pm.input_price_per_million,
                'output_price': pm.output_price_per_million
            }
        
        return model_pricing
    
    @classmethod
    def _calculate_cost(cls, input_tokens: int, output_tokens: int, model: str, pricing: Dict[str, Dict[str, float]]) -> float:
        """Calculate cost for given token counts and model"""
        if model not in pricing:
            return 0.0
        
        model_price = pricing[model]
        input_cost = (input_tokens / 1_000_000) * model_price['input_price']
        output_cost = (output_tokens / 1_000_000) * model_price['output_price']
        return input_cost + output_cost
    
    @classmethod
    async def calculate_statistics_for_period(
        cls,
        db: AsyncSession,
        period_start: datetime,
        period_end: datetime,
        period_type: str
    ) -> int:
        """
        Calculate statistics for a specific period and store them in the database.
        Returns the number of statistics records created.
        """
        logger.info(f"Calculating statistics for {period_type} from {period_start} to {period_end}")
        
        # Get model pricing
        pricing = await cls._get_model_pricing(db)
        
        # Delete existing statistics for this period
        await db.execute(
            delete(JobStatistics).where(
                and_(
                    JobStatistics.period_type == period_type,
                    JobStatistics.period_start == period_start,
                    JobStatistics.period_end == period_end
                )
            )
        )
        
        # Get jobs for the period
        jobs_result = await db.execute(
            select(Job).where(
                and_(
                    Job.created_at >= period_start,
                    Job.created_at < period_end
                )
            )
        )
        jobs = jobs_result.scalars().all()
        
        if not jobs:
            logger.info(f"No jobs found for period {period_start} to {period_end}")
            return 0
        
        # Aggregate by agent name
        agent_stats = {}
        for job in jobs:
            if job.name not in agent_stats:
                agent_stats[job.name] = {
                    'job_count': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_cost': 0.0,
                    'total_duration': 0,
                    'duration_count': 0
                }
            
            stats = agent_stats[job.name]
            stats['job_count'] += 1
            stats['total_input_tokens'] += job.token_count or 0
            stats['total_output_tokens'] += job.output_token_count or 0
            stats['total_cost'] += cls._calculate_cost(
                job.token_count or 0,
                job.output_token_count or 0,
                job.model,
                pricing
            )
            
            if job.duration is not None:
                stats['total_duration'] += job.duration
                stats['duration_count'] += 1
        
        # Aggregate by provider
        provider_stats = {}
        for job in jobs:
            if job.provider not in provider_stats:
                provider_stats[job.provider] = {
                    'job_count': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_cost': 0.0
                }
            
            stats = provider_stats[job.provider]
            stats['job_count'] += 1
            stats['total_input_tokens'] += job.token_count or 0
            stats['total_output_tokens'] += job.output_token_count or 0
            stats['total_cost'] += cls._calculate_cost(
                job.token_count or 0,
                job.output_token_count or 0,
                job.model,
                pricing
            )
        
        # Aggregate by model
        model_stats = {}
        for job in jobs:
            if job.model not in model_stats:
                model_stats[job.model] = {
                    'job_count': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_cost': 0.0
                }
            
            stats = model_stats[job.model]
            stats['job_count'] += 1
            stats['total_input_tokens'] += job.token_count or 0
            stats['total_output_tokens'] += job.output_token_count or 0
            stats['total_cost'] += cls._calculate_cost(
                job.token_count or 0,
                job.output_token_count or 0,
                job.model,
                pricing
            )
        
        # Store statistics in database
        records_created = 0
        
        # Store agent statistics
        for agent_name, stats in agent_stats.items():
            avg_duration = None
            if stats['duration_count'] > 0:
                avg_duration = stats['total_duration'] / stats['duration_count']
            
            db_stat = JobStatistics(
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                agent_name=agent_name,
                job_count=stats['job_count'],
                total_input_tokens=stats['total_input_tokens'],
                total_output_tokens=stats['total_output_tokens'],
                total_cost=stats['total_cost'],
                avg_duration=avg_duration
            )
            db.add(db_stat)
            records_created += 1
        
        # Store provider statistics
        for provider, stats in provider_stats.items():
            db_stat = JobStatistics(
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                provider=provider,
                job_count=stats['job_count'],
                total_input_tokens=stats['total_input_tokens'],
                total_output_tokens=stats['total_output_tokens'],
                total_cost=stats['total_cost']
            )
            db.add(db_stat)
            records_created += 1
        
        # Store model statistics
        for model, stats in model_stats.items():
            db_stat = JobStatistics(
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                model=model,
                job_count=stats['job_count'],
                total_input_tokens=stats['total_input_tokens'],
                total_output_tokens=stats['total_output_tokens'],
                total_cost=stats['total_cost']
            )
            db.add(db_stat)
            records_created += 1
        
        await db.flush()
        logger.info(f"Created {records_created} statistics records for {period_type}")
        
        return records_created
    
    @classmethod
    async def calculate_all_statistics(cls, db: AsyncSession) -> Dict[str, int]:
        """
        Calculate statistics for all time periods (day, week, month).
        Returns count of statistics created for each period type.
        """
        now = datetime.now(timezone.utc)
        counts = {'day': 0, 'week': 0, 'month': 0}
        
        # Calculate daily statistics for the last 30 days
        for i in range(30):
            day_start = (now - timedelta(days=i+1)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count = await cls.calculate_statistics_for_period(db, day_start, day_end, 'day')
            counts['day'] += count
        
        # Calculate weekly statistics for the last 12 weeks
        for i in range(12):
            week_start = (now - timedelta(weeks=i+1)).replace(hour=0, minute=0, second=0, microsecond=0)
            # Adjust to start of week (Monday)
            week_start = week_start - timedelta(days=week_start.weekday())
            week_end = week_start + timedelta(weeks=1)
            count = await cls.calculate_statistics_for_period(db, week_start, week_end, 'week')
            counts['week'] += count
        
        # Calculate monthly statistics for the last 12 months
        for i in range(12):
            # Calculate month start
            month_date = now - timedelta(days=30 * (i + 1))
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate month end (first day of next month)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            count = await cls.calculate_statistics_for_period(db, month_start, month_end, 'month')
            counts['month'] += count
        
        await db.commit()
        logger.info(f"Calculated all statistics: {counts}")
        
        return counts
    
    @classmethod
    async def get_statistics_by_agent(
        cls,
        db: AsyncSession,
        period_type: str = 'month',
        limit: int = 12
    ) -> List[JobStatisticsSummary]:
        """Get aggregated statistics by agent name for the specified period"""
        result = await db.execute(
            select(
                JobStatistics.agent_name.label('label'),
                func.sum(JobStatistics.job_count).label('job_count'),
                func.sum(JobStatistics.total_input_tokens).label('total_input_tokens'),
                func.sum(JobStatistics.total_output_tokens).label('total_output_tokens'),
                func.sum(JobStatistics.total_cost).label('total_cost'),
                func.avg(JobStatistics.avg_duration).label('avg_duration')
            )
            .where(
                and_(
                    JobStatistics.period_type == period_type,
                    JobStatistics.agent_name.isnot(None)
                )
            )
            .group_by(JobStatistics.agent_name)
            .order_by(func.sum(JobStatistics.total_cost).desc())
            .limit(limit)
        )
        
        rows = result.all()
        return [
            JobStatisticsSummary(
                label=row.label or 'Unknown',
                job_count=int(row.job_count or 0),
                total_input_tokens=int(row.total_input_tokens or 0),
                total_output_tokens=int(row.total_output_tokens or 0),
                total_cost=float(row.total_cost or 0.0),
                avg_duration=float(row.avg_duration) if row.avg_duration else None
            )
            for row in rows
        ]
    
    @classmethod
    async def get_statistics_by_provider(
        cls,
        db: AsyncSession,
        period_type: str = 'month',
        limit: int = 12
    ) -> List[JobStatisticsSummary]:
        """Get aggregated statistics by provider for the specified period"""
        result = await db.execute(
            select(
                JobStatistics.provider.label('label'),
                func.sum(JobStatistics.job_count).label('job_count'),
                func.sum(JobStatistics.total_input_tokens).label('total_input_tokens'),
                func.sum(JobStatistics.total_output_tokens).label('total_output_tokens'),
                func.sum(JobStatistics.total_cost).label('total_cost'),
                func.avg(JobStatistics.avg_duration).label('avg_duration')
            )
            .where(
                and_(
                    JobStatistics.period_type == period_type,
                    JobStatistics.provider.isnot(None)
                )
            )
            .group_by(JobStatistics.provider)
            .order_by(func.sum(JobStatistics.total_cost).desc())
            .limit(limit)
        )
        
        rows = result.all()
        return [
            JobStatisticsSummary(
                label=row.label or 'Unknown',
                job_count=int(row.job_count or 0),
                total_input_tokens=int(row.total_input_tokens or 0),
                total_output_tokens=int(row.total_output_tokens or 0),
                total_cost=float(row.total_cost or 0.0),
                avg_duration=float(row.avg_duration) if row.avg_duration else None
            )
            for row in rows
        ]
    
    @classmethod
    async def get_statistics_by_model(
        cls,
        db: AsyncSession,
        period_type: str = 'month',
        limit: int = 12
    ) -> List[JobStatisticsSummary]:
        """Get aggregated statistics by model for the specified period"""
        result = await db.execute(
            select(
                JobStatistics.model.label('label'),
                func.sum(JobStatistics.job_count).label('job_count'),
                func.sum(JobStatistics.total_input_tokens).label('total_input_tokens'),
                func.sum(JobStatistics.total_output_tokens).label('total_output_tokens'),
                func.sum(JobStatistics.total_cost).label('total_cost'),
                func.avg(JobStatistics.avg_duration).label('avg_duration')
            )
            .where(
                and_(
                    JobStatistics.period_type == period_type,
                    JobStatistics.model.isnot(None)
                )
            )
            .group_by(JobStatistics.model)
            .order_by(func.sum(JobStatistics.total_cost).desc())
            .limit(limit)
        )
        
        rows = result.all()
        return [
            JobStatisticsSummary(
                label=row.label or 'Unknown',
                job_count=int(row.job_count or 0),
                total_input_tokens=int(row.total_input_tokens or 0),
                total_output_tokens=int(row.total_output_tokens or 0),
                total_cost=float(row.total_cost or 0.0),
                avg_duration=float(row.avg_duration) if row.avg_duration else None
            )
            for row in rows
        ]
    
    @classmethod
    async def get_time_series_data(
        cls,
        db: AsyncSession,
        period_type: str = 'month',
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """Get time series data for the specified period type"""
        result = await db.execute(
            select(
                JobStatistics.period_start,
                func.sum(JobStatistics.job_count).label('job_count'),
                func.sum(JobStatistics.total_input_tokens).label('total_input_tokens'),
                func.sum(JobStatistics.total_output_tokens).label('total_output_tokens'),
                func.sum(JobStatistics.total_cost).label('total_cost')
            )
            .where(JobStatistics.period_type == period_type)
            .group_by(JobStatistics.period_start)
            .order_by(JobStatistics.period_start.desc())
            .limit(limit)
        )
        
        rows = result.all()
        return [
            {
                'period_start': row.period_start,
                'job_count': int(row.job_count or 0),
                'total_input_tokens': int(row.total_input_tokens or 0),
                'total_output_tokens': int(row.total_output_tokens or 0),
                'total_cost': float(row.total_cost or 0.0)
            }
            for row in reversed(rows)  # Reverse to get chronological order
        ]
