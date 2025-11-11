"""
Tests for Jobs cost calculation with output tokens and provider model pricing
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from model.user import User, Base
from model.job import Job
from model.provider import Provider, ProviderModel
from service.job_service import JobService
from service.provider_service import ProviderService


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
async def test_user(async_session):
    """Create a test user"""
    user = User(
        client_id="test-user-1",
        client_secret="secret1",
        name="Test User",
        email="user@test.com",
        role="user",
        is_active=True
    )
    
    async_session.add(user)
    await async_session.commit()
    
    return user


@pytest_asyncio.fixture
async def test_provider_with_models(async_session):
    """Create a test provider with models that have pricing"""
    # Create provider
    provider = Provider(
        id="provider-1",
        name="OpenAI",
        provider_type="openai",
        api_key="test-key",
        is_active=True
    )
    async_session.add(provider)
    await async_session.flush()
    
    # Create model with pricing
    model1 = ProviderModel(
        id="model-1",
        provider_id=provider.id,
        model_name="GPT-4",
        model_id="gpt-4",
        is_active=True,
        input_price_per_million=30.0,  # $30 per 1M input tokens
        output_price_per_million=60.0  # $60 per 1M output tokens
    )
    
    model2 = ProviderModel(
        id="model-2",
        provider_id=provider.id,
        model_name="GPT-3.5 Turbo",
        model_id="gpt-3.5-turbo",
        is_active=True,
        input_price_per_million=0.5,   # $0.50 per 1M input tokens
        output_price_per_million=1.5   # $1.50 per 1M output tokens
    )
    
    # Model without pricing
    model3 = ProviderModel(
        id="model-3",
        provider_id=provider.id,
        model_name="GPT-4-Turbo",
        model_id="gpt-4-turbo",
        is_active=True,
        input_price_per_million=None,
        output_price_per_million=None
    )
    
    async_session.add(model1)
    async_session.add(model2)
    async_session.add(model3)
    await async_session.commit()
    
    return provider, [model1, model2, model3]


@pytest.mark.asyncio
async def test_job_with_output_tokens(async_session, test_user):
    """Test creating a job with both input and output tokens"""
    from model.job import JobCreate
    
    job_data = JobCreate(
        name="Test Job",
        user_id=test_user.client_id,
        provider="openai",
        model="gpt-4",
        status="completed",
        token_count=1000,
        output_token_count=500
    )
    
    job = await JobService.create_job(async_session, job_data)
    await async_session.commit()
    
    # Verify job was created with correct token counts
    assert job.token_count == 1000
    assert job.output_token_count == 500


@pytest.mark.asyncio
async def test_update_output_token_count(async_session, test_user):
    """Test updating output token count for a job"""
    from model.job import JobCreate
    
    # Create job
    job_data = JobCreate(
        name="Test Job",
        user_id=test_user.client_id,
        provider="openai",
        model="gpt-4",
        status="processing",
        token_count=1000
    )
    
    job = await JobService.create_job(async_session, job_data)
    await async_session.commit()
    
    # Update output token count
    success = await JobService.update_job_output_token_count(
        async_session, job.id, 750
    )
    await async_session.commit()
    
    assert success is True
    
    # Verify update
    updated_job = await JobService.get_job_by_id(async_session, job.id)
    assert updated_job.output_token_count == 750


@pytest.mark.asyncio
async def test_cost_calculation_with_pricing(async_session, test_user, test_provider_with_models):
    """Test cost calculation for jobs with model pricing"""
    from model.job import JobCreate
    from admin_routes import _enrich_jobs_with_costs
    
    provider, models = test_provider_with_models
    
    # Create job with GPT-4 (has pricing)
    job_data = JobCreate(
        name="GPT-4 Job",
        user_id=test_user.client_id,
        provider="openai",
        model="gpt-4",
        status="completed",
        token_count=100_000,      # 100k input tokens
        output_token_count=50_000  # 50k output tokens
    )
    
    job = await JobService.create_job(async_session, job_data)
    await async_session.commit()
    
    # Get jobs
    jobs, _ = await JobService.get_jobs_paginated(async_session, page=1, per_page=10)
    
    # Enrich with costs
    await _enrich_jobs_with_costs(async_session, jobs)
    
    # Verify cost calculation
    # Input: 100,000 / 1,000,000 * 30.0 = 3.0
    # Output: 50,000 / 1,000,000 * 60.0 = 3.0
    # Total: 6.0
    assert jobs[0]['estimated_cost'] is not None
    assert abs(jobs[0]['estimated_cost'] - 6.0) < 0.0001


@pytest.mark.asyncio
async def test_cost_calculation_cheap_model(async_session, test_user, test_provider_with_models):
    """Test cost calculation for cheaper model (GPT-3.5 Turbo)"""
    from model.job import JobCreate
    from admin_routes import _enrich_jobs_with_costs
    
    provider, models = test_provider_with_models
    
    # Create job with GPT-3.5 Turbo
    job_data = JobCreate(
        name="GPT-3.5 Job",
        user_id=test_user.client_id,
        provider="openai",
        model="gpt-3.5-turbo",
        status="completed",
        token_count=500_000,      # 500k input tokens
        output_token_count=200_000 # 200k output tokens
    )
    
    job = await JobService.create_job(async_session, job_data)
    await async_session.commit()
    
    # Get jobs
    jobs, _ = await JobService.get_jobs_paginated(async_session, page=1, per_page=10)
    
    # Enrich with costs
    await _enrich_jobs_with_costs(async_session, jobs)
    
    # Verify cost calculation
    # Input: 500,000 / 1,000,000 * 0.5 = 0.25
    # Output: 200,000 / 1,000,000 * 1.5 = 0.3
    # Total: 0.55
    assert jobs[0]['estimated_cost'] is not None
    assert abs(jobs[0]['estimated_cost'] - 0.55) < 0.0001


@pytest.mark.asyncio
async def test_cost_calculation_no_pricing(async_session, test_user, test_provider_with_models):
    """Test that jobs without pricing show None for estimated cost"""
    from model.job import JobCreate
    from admin_routes import _enrich_jobs_with_costs
    
    provider, models = test_provider_with_models
    
    # Create job with model that has no pricing
    job_data = JobCreate(
        name="No Pricing Job",
        user_id=test_user.client_id,
        provider="openai",
        model="gpt-4-turbo",  # This model has no pricing
        status="completed",
        token_count=100_000,
        output_token_count=50_000
    )
    
    job = await JobService.create_job(async_session, job_data)
    await async_session.commit()
    
    # Get jobs
    jobs, _ = await JobService.get_jobs_paginated(async_session, page=1, per_page=10)
    
    # Enrich with costs
    await _enrich_jobs_with_costs(async_session, jobs)
    
    # Verify cost is None
    assert jobs[0]['estimated_cost'] is None


@pytest.mark.asyncio
async def test_cost_calculation_missing_tokens(async_session, test_user, test_provider_with_models):
    """Test cost calculation when token counts are missing"""
    from model.job import JobCreate
    from admin_routes import _enrich_jobs_with_costs
    
    provider, models = test_provider_with_models
    
    # Create job without token counts
    job_data = JobCreate(
        name="No Tokens Job",
        user_id=test_user.client_id,
        provider="openai",
        model="gpt-4",
        status="completed"
    )
    
    job = await JobService.create_job(async_session, job_data)
    await async_session.commit()
    
    # Get jobs
    jobs, _ = await JobService.get_jobs_paginated(async_session, page=1, per_page=10)
    
    # Enrich with costs
    await _enrich_jobs_with_costs(async_session, jobs)
    
    # Verify cost is 0 (no tokens = no cost)
    assert jobs[0]['estimated_cost'] is not None
    assert abs(jobs[0]['estimated_cost'] - 0.0) < 0.0001


@pytest.mark.asyncio
async def test_provider_model_create_with_pricing(async_session):
    """Test creating a provider model with pricing information"""
    from model.provider import ProviderModelCreate
    
    # Create provider first
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        provider_type="openai",
        is_active=True
    )
    async_session.add(provider)
    await async_session.commit()
    
    # Create model with pricing
    model_data = ProviderModelCreate(
        provider_id=provider.id,
        model_name="Test Model",
        model_id="test-model",
        is_active=True,
        input_price_per_million=10.0,
        output_price_per_million=20.0
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Verify pricing was set
    assert model.input_price_per_million == 10.0
    assert model.output_price_per_million == 20.0


@pytest.mark.asyncio
async def test_provider_model_update_pricing(async_session):
    """Test updating pricing information for a provider model"""
    from model.provider import ProviderModelCreate, ProviderModelUpdate
    
    # Create provider
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        provider_type="openai",
        is_active=True
    )
    async_session.add(provider)
    await async_session.commit()
    
    # Create model
    model_data = ProviderModelCreate(
        provider_id=provider.id,
        model_name="Test Model",
        model_id="test-model",
        is_active=True,
        input_price_per_million=10.0,
        output_price_per_million=20.0
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Update pricing
    update_data = ProviderModelUpdate(
        input_price_per_million=15.0,
        output_price_per_million=30.0
    )
    
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    # Verify pricing was updated
    assert updated_model.input_price_per_million == 15.0
    assert updated_model.output_price_per_million == 30.0


@pytest.mark.asyncio
async def test_multiple_jobs_cost_calculation(async_session, test_user, test_provider_with_models):
    """Test cost calculation for multiple jobs with different models"""
    from model.job import JobCreate
    from admin_routes import _enrich_jobs_with_costs
    
    provider, models = test_provider_with_models
    
    # Create multiple jobs with different models
    jobs_data = [
        JobCreate(
            name="GPT-4 Job",
            user_id=test_user.client_id,
            provider="openai",
            model="gpt-4",
            status="completed",
            token_count=100_000,
            output_token_count=50_000
        ),
        JobCreate(
            name="GPT-3.5 Job",
            user_id=test_user.client_id,
            provider="openai",
            model="gpt-3.5-turbo",
            status="completed",
            token_count=200_000,
            output_token_count=100_000
        ),
        JobCreate(
            name="No Pricing Job",
            user_id=test_user.client_id,
            provider="openai",
            model="unknown-model",
            status="completed",
            token_count=50_000,
            output_token_count=25_000
        )
    ]
    
    for job_data in jobs_data:
        await JobService.create_job(async_session, job_data)
    await async_session.commit()
    
    # Get all jobs
    jobs, total = await JobService.get_jobs_paginated(async_session, page=1, per_page=10)
    
    # Enrich with costs
    await _enrich_jobs_with_costs(async_session, jobs)
    
    # Verify we have 3 jobs
    assert total == 3
    
    # Find and verify each job's cost
    gpt4_job = next(j for j in jobs if j['model'] == 'gpt-4')
    gpt35_job = next(j for j in jobs if j['model'] == 'gpt-3.5-turbo')
    unknown_job = next(j for j in jobs if j['model'] == 'unknown-model')
    
    # GPT-4: (100k/1M * 30) + (50k/1M * 60) = 3.0 + 3.0 = 6.0
    assert abs(gpt4_job['estimated_cost'] - 6.0) < 0.0001
    
    # GPT-3.5: (200k/1M * 0.5) + (100k/1M * 1.5) = 0.1 + 0.15 = 0.25
    assert abs(gpt35_job['estimated_cost'] - 0.25) < 0.0001
    
    # Unknown model: no pricing
    assert unknown_job['estimated_cost'] is None
