"""
Test provider functionality
"""
import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from model.user import Base
from model.provider import Provider, ProviderModel, ProviderCreate, ProviderModelCreate
from service.provider_service import ProviderService


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session"""
    # Use in-memory SQLite database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_provider(db_session):
    """Test creating a provider"""
    provider_data = ProviderCreate(
        name="Test OpenAI",
        provider_type="openai",
        api_key="test-key",
        organization_id="test-org",
        is_active=True
    )
    
    provider = await ProviderService.create_provider(db_session, provider_data)
    await db_session.commit()
    
    assert provider.name == "Test OpenAI"
    assert provider.provider_type == "openai"
    assert provider.api_key == "test-key"
    assert provider.organization_id == "test-org"
    assert provider.is_active is True
    assert provider.id is not None


@pytest.mark.asyncio
async def test_get_all_providers(db_session):
    """Test getting all providers"""
    # Create test providers
    provider1 = ProviderCreate(name="Provider 1", provider_type="openai", api_key="key1", is_active=True)
    provider2 = ProviderCreate(name="Provider 2", provider_type="gemini", api_key="key2", is_active=False)
    
    await ProviderService.create_provider(db_session, provider1)
    await ProviderService.create_provider(db_session, provider2)
    await db_session.commit()
    
    providers = await ProviderService.get_all_providers(db_session)
    
    assert len(providers) == 2
    assert providers[0].name in ["Provider 1", "Provider 2"]


@pytest.mark.asyncio
async def test_create_provider_model(db_session):
    """Test creating a provider model"""
    # First create a provider
    provider_data = ProviderCreate(
        name="Test Provider",
        provider_type="openai",
        api_key="test-key",
        is_active=True
    )
    provider = await ProviderService.create_provider(db_session, provider_data)
    await db_session.commit()
    
    # Create a model
    model_data = ProviderModelCreate(
        provider_id=provider.id,
        model_name="GPT-4",
        model_id="gpt-4",
        is_active=True
    )
    
    model = await ProviderService.create_provider_model(db_session, model_data)
    await db_session.commit()
    
    assert model.provider_id == provider.id
    assert model.model_name == "GPT-4"
    assert model.model_id == "gpt-4"
    assert model.is_active is True


@pytest.mark.asyncio
async def test_get_provider_models(db_session):
    """Test getting models for a provider"""
    # Create provider
    provider_data = ProviderCreate(name="Test Provider", provider_type="openai", api_key="key", is_active=True)
    provider = await ProviderService.create_provider(db_session, provider_data)
    await db_session.commit()
    
    # Create models
    model1 = ProviderModelCreate(provider_id=provider.id, model_name="Model 1", model_id="model-1", is_active=True)
    model2 = ProviderModelCreate(provider_id=provider.id, model_name="Model 2", model_id="model-2", is_active=False)
    
    await ProviderService.create_provider_model(db_session, model1)
    await ProviderService.create_provider_model(db_session, model2)
    await db_session.commit()
    
    # Get all models
    all_models = await ProviderService.get_provider_models(db_session, provider.id)
    assert len(all_models) == 2
    
    # Get active models only
    active_models = await ProviderService.get_provider_models(db_session, provider.id, active_only=True)
    assert len(active_models) == 1
    assert active_models[0].model_name == "Model 1"


@pytest.mark.asyncio
async def test_update_provider(db_session):
    """Test updating a provider"""
    # Create provider
    provider_data = ProviderCreate(name="Original", provider_type="openai", api_key="key", is_active=True)
    provider = await ProviderService.create_provider(db_session, provider_data)
    await db_session.commit()
    
    # Update provider
    from model.provider import ProviderUpdate
    update_data = ProviderUpdate(name="Updated", is_active=False)
    updated = await ProviderService.update_provider(db_session, provider.id, update_data)
    await db_session.commit()
    
    assert updated.name == "Updated"
    assert updated.is_active is False
    assert updated.api_key == "key"  # Unchanged


@pytest.mark.asyncio
async def test_delete_provider(db_session):
    """Test deleting a provider"""
    # Create provider
    provider_data = ProviderCreate(name="To Delete", provider_type="openai", api_key="key", is_active=True)
    provider = await ProviderService.create_provider(db_session, provider_data)
    await db_session.commit()
    
    # Delete provider
    success = await ProviderService.delete_provider(db_session, provider.id)
    await db_session.commit()
    
    assert success is True
    
    # Verify deletion
    deleted_provider = await ProviderService.get_provider(db_session, provider.id)
    assert deleted_provider is None


@pytest.mark.asyncio
async def test_get_provider_by_name(db_session):
    """Test getting a provider by name"""
    # Create provider
    provider_data = ProviderCreate(name="Unique Name", provider_type="openai", api_key="key", is_active=True)
    await ProviderService.create_provider(db_session, provider_data)
    await db_session.commit()
    
    # Get by name
    provider = await ProviderService.get_provider_by_name(db_session, "Unique Name")
    
    assert provider is not None
    assert provider.name == "Unique Name"
    assert provider.provider_type == "openai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
