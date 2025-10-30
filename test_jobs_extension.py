"""
Tests for Jobs ListView extensions - filtering, cleanup, and user display
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from model.user import User, Base
from model.job import Job
from service.job_service import JobService


@pytest_asyncio.fixture
async def async_session():
    """Create async test database session"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_users(async_session):
    """Create test users"""
    user1 = User(
        client_id="user-1",
        client_secret="secret1",
        name="Test User 1",
        email="user1@test.com",
        role="user",
        is_active=True
    )
    user2 = User(
        client_id="user-2",
        client_secret="secret2",
        name="Test User 2",
        email="user2@test.com",
        role="user",
        is_active=True
    )
    
    async_session.add(user1)
    async_session.add(user2)
    await async_session.commit()
    
    return [user1, user2]


@pytest_asyncio.fixture
async def test_jobs(async_session, test_users):
    """Create test jobs with different statuses, providers, and dates"""
    jobs = []
    
    # Recent jobs
    for i in range(5):
        job = Job(
            id=f"job-{i}",
            name=f"Recent Job {i}",
            user_id=test_users[i % 2].client_id,
            provider="openai" if i % 2 == 0 else "anthropic",
            model="gpt-4" if i % 2 == 0 else "claude-3",
            status="completed" if i % 3 == 0 else "processing",
            created_at=datetime.now(timezone.utc) - timedelta(days=i)
        )
        jobs.append(job)
        async_session.add(job)
    
    # Old jobs (older than 7 days)
    for i in range(3):
        job = Job(
            id=f"old-job-{i}",
            name=f"Old Job {i}",
            user_id=test_users[0].client_id,
            provider="openai",
            model="gpt-3.5-turbo",
            status="completed",
            created_at=datetime.now(timezone.utc) - timedelta(days=8 + i)
        )
        jobs.append(job)
        async_session.add(job)
    
    await async_session.commit()
    
    return jobs


@pytest.mark.asyncio
async def test_get_jobs_with_user_names(async_session, test_jobs, test_users):
    """Test that jobs are returned with user names instead of just IDs"""
    jobs, total_count = await JobService.get_jobs_paginated(async_session, page=1, per_page=10)
    
    assert total_count == 8  # 5 recent + 3 old
    assert len(jobs) == 8
    
    # Check that user_name is included
    for job in jobs:
        assert 'user_name' in job
        assert job['user_name'] in ['Test User 1', 'Test User 2']
        assert job['user_id'] in ['user-1', 'user-2']


@pytest.mark.asyncio
async def test_filter_by_status(async_session, test_jobs):
    """Test filtering jobs by status"""
    # Filter for completed jobs
    jobs, total_count = await JobService.get_jobs_paginated(
        async_session, page=1, per_page=10, status_filter="completed"
    )
    
    # Should have 2 recent completed + 3 old completed = 5
    assert total_count == 5
    assert all(job['status'] == 'completed' for job in jobs)


@pytest.mark.asyncio
async def test_filter_by_provider(async_session, test_jobs):
    """Test filtering jobs by provider"""
    # Filter for openai provider
    jobs, total_count = await JobService.get_jobs_paginated(
        async_session, page=1, per_page=10, provider_filter="openai"
    )
    
    # Should have 3 recent openai (0, 2, 4) + 3 old openai = 6
    assert total_count == 6
    assert all(job['provider'] == 'openai' for job in jobs)


@pytest.mark.asyncio
async def test_filter_by_name(async_session, test_jobs):
    """Test filtering jobs by name"""
    # Filter for jobs with "Recent" in name
    jobs, total_count = await JobService.get_jobs_paginated(
        async_session, page=1, per_page=10, name_filter="Recent"
    )
    
    assert total_count == 5
    assert all('Recent' in job['name'] for job in jobs)
    
    # Filter for jobs with "Old" in name
    jobs, total_count = await JobService.get_jobs_paginated(
        async_session, page=1, per_page=10, name_filter="Old"
    )
    
    assert total_count == 3
    assert all('Old' in job['name'] for job in jobs)


@pytest.mark.asyncio
async def test_combined_filters(async_session, test_jobs):
    """Test combining multiple filters"""
    # Filter for completed openai jobs
    jobs, total_count = await JobService.get_jobs_paginated(
        async_session, 
        page=1, 
        per_page=10,
        status_filter="completed",
        provider_filter="openai"
    )
    
    # Should have 2 recent completed openai (job-0 at index 0, job-3 at index 3 is processing, not completed)
    # job-0 is completed openai, job-2 is processing openai, job-4 is processing openai
    # So actually only job-0 from recent + 3 old = 4
    assert total_count == 4
    assert all(job['status'] == 'completed' and job['provider'] == 'openai' for job in jobs)


@pytest.mark.asyncio
async def test_delete_old_jobs(async_session, test_jobs):
    """Test deleting jobs older than 7 days"""
    # Verify we have 8 jobs initially
    jobs_before, count_before = await JobService.get_jobs_paginated(async_session, page=1, per_page=20)
    assert count_before == 8
    
    # Delete old jobs
    deleted_count = await JobService.delete_old_jobs(async_session, days=7)
    await async_session.commit()
    
    # Should have deleted 3 old jobs
    assert deleted_count == 3
    
    # Verify we now have 5 jobs
    jobs_after, count_after = await JobService.get_jobs_paginated(async_session, page=1, per_page=20)
    assert count_after == 5
    
    # Verify only recent jobs remain
    for job in jobs_after:
        assert 'Recent' in job['name']


@pytest.mark.asyncio
async def test_pagination_with_filters(async_session, test_jobs):
    """Test pagination works correctly with filters"""
    # Get page 1 with 2 items per page, filtered by openai
    jobs_p1, total_count = await JobService.get_jobs_paginated(
        async_session, 
        page=1, 
        per_page=2,
        provider_filter="openai"
    )
    
    assert total_count == 6
    assert len(jobs_p1) == 2
    
    # Get page 2
    jobs_p2, _ = await JobService.get_jobs_paginated(
        async_session, 
        page=2, 
        per_page=2,
        provider_filter="openai"
    )
    
    assert len(jobs_p2) == 2
    
    # Verify no overlap
    job_ids_p1 = [j['id'] for j in jobs_p1]
    job_ids_p2 = [j['id'] for j in jobs_p2]
    assert len(set(job_ids_p1) & set(job_ids_p2)) == 0


@pytest.mark.asyncio
async def test_user_name_with_missing_user(async_session, test_users):
    """Test that jobs with non-existent users show 'Unbekannt'"""
    # Create a job with a non-existent user_id
    job = Job(
        id="orphan-job",
        name="Orphan Job",
        user_id="non-existent-user",
        provider="openai",
        model="gpt-4",
        status="completed",
        created_at=datetime.now(timezone.utc)
    )
    async_session.add(job)
    await async_session.commit()
    
    # Get jobs
    jobs, total_count = await JobService.get_jobs_paginated(async_session, page=1, per_page=10)
    
    # Find the orphan job
    orphan_job = next(j for j in jobs if j['id'] == 'orphan-job')
    assert orphan_job['user_name'] == 'Unbekannt'
    assert orphan_job['user_id'] == 'non-existent-user'
