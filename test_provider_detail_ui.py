"""
Tests for Provider Detail UI with Model Pricing Management
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from model.user import Base
from model.provider import Provider, ProviderModel, ProviderModelCreate, ProviderModelUpdate
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
async def test_provider(async_session):
    """Create a test provider"""
    provider = Provider(
        id="test-provider-1",
        name="Test OpenAI",
        provider_type="openai",
        api_key="sk-test-key",
        is_active=True
    )
    async_session.add(provider)
    await async_session.commit()
    return provider


@pytest.mark.asyncio
async def test_create_model_with_pricing(async_session, test_provider):
    """Test creating a model with input and output pricing"""
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="GPT-4",
        model_id="gpt-4",
        is_active=True,
        input_price_per_million=30.0,
        output_price_per_million=60.0
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    assert model.model_name == "GPT-4"
    assert model.model_id == "gpt-4"
    assert model.input_price_per_million == 30.0
    assert model.output_price_per_million == 60.0
    assert model.is_active is True


@pytest.mark.asyncio
async def test_update_model_pricing(async_session, test_provider):
    """Test updating model pricing"""
    # Create model
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="GPT-3.5 Turbo",
        model_id="gpt-3.5-turbo",
        is_active=True,
        input_price_per_million=0.5,
        output_price_per_million=1.5
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Update pricing
    update_data = ProviderModelUpdate(
        input_price_per_million=0.75,
        output_price_per_million=2.0
    )
    
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    assert updated_model.input_price_per_million == 0.75
    assert updated_model.output_price_per_million == 2.0
    assert updated_model.model_name == "GPT-3.5 Turbo"  # Name unchanged


@pytest.mark.asyncio
async def test_update_model_name_and_status(async_session, test_provider):
    """Test updating model name and active status"""
    # Create model
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="Test Model",
        model_id="test-model",
        is_active=True,
        input_price_per_million=10.0,
        output_price_per_million=20.0
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Update name and status
    update_data = ProviderModelUpdate(
        model_name="Updated Test Model",
        is_active=False
    )
    
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    assert updated_model.model_name == "Updated Test Model"
    assert updated_model.is_active is False
    # Pricing should remain unchanged
    assert updated_model.input_price_per_million == 10.0
    assert updated_model.output_price_per_million == 20.0


@pytest.mark.asyncio
async def test_delete_model(async_session, test_provider):
    """Test deleting a provider model"""
    # Create model
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="Model to Delete",
        model_id="delete-me",
        is_active=True
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Delete model
    success = await ProviderService.delete_provider_model(async_session, model.id)
    await async_session.commit()
    
    assert success is True
    
    # Verify model is deleted
    models = await ProviderService.get_provider_models(async_session, test_provider.id)
    assert len(models) == 0


@pytest.mark.asyncio
async def test_get_provider_with_models(async_session, test_provider):
    """Test getting provider with all its models including pricing"""
    # Create multiple models with different pricing
    models_data = [
        ProviderModelCreate(
            provider_id=test_provider.id,
            model_name="GPT-4",
            model_id="gpt-4",
            is_active=True,
            input_price_per_million=30.0,
            output_price_per_million=60.0
        ),
        ProviderModelCreate(
            provider_id=test_provider.id,
            model_name="GPT-3.5",
            model_id="gpt-3.5-turbo",
            is_active=True,
            input_price_per_million=0.5,
            output_price_per_million=1.5
        ),
        ProviderModelCreate(
            provider_id=test_provider.id,
            model_name="No Pricing Model",
            model_id="no-price",
            is_active=False,
            input_price_per_million=None,
            output_price_per_million=None
        ),
    ]
    
    for model_data in models_data:
        await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Get provider with models
    provider = await ProviderService.get_provider(async_session, test_provider.id, include_models=True)
    
    assert provider is not None
    assert len(provider.models) == 3
    
    # Verify each model has correct pricing
    gpt4 = next(m for m in provider.models if m.model_id == "gpt-4")
    assert gpt4.input_price_per_million == 30.0
    assert gpt4.output_price_per_million == 60.0
    
    gpt35 = next(m for m in provider.models if m.model_id == "gpt-3.5-turbo")
    assert gpt35.input_price_per_million == 0.5
    assert gpt35.output_price_per_million == 1.5
    
    no_price = next(m for m in provider.models if m.model_id == "no-price")
    assert no_price.input_price_per_million is None
    assert no_price.output_price_per_million is None


@pytest.mark.asyncio
async def test_model_pricing_optional(async_session, test_provider):
    """Test that pricing fields are optional when creating models"""
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="Model Without Price",
        model_id="no-pricing",
        is_active=True,
        input_price_per_million=None,
        output_price_per_million=None
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    assert model.model_name == "Model Without Price"
    assert model.input_price_per_million is None
    assert model.output_price_per_million is None


@pytest.mark.asyncio
async def test_partial_pricing_update(async_session, test_provider):
    """Test updating only input or output pricing"""
    # Create model with pricing
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="Partial Update Model",
        model_id="partial-update",
        is_active=True,
        input_price_per_million=10.0,
        output_price_per_million=20.0
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Update only input pricing
    update_data = ProviderModelUpdate(
        input_price_per_million=15.0
    )
    
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    assert updated_model.input_price_per_million == 15.0
    assert updated_model.output_price_per_million == 20.0  # Unchanged
