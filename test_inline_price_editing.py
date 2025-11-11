"""
Tests for Inline Price Editing with htmx
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
async def test_inline_update_input_price_only(async_session, test_provider):
    """Test inline updating only input price without changing other fields"""
    # Create model with both prices
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
    
    # Update only input price (simulating inline editing)
    update_data = ProviderModelUpdate(input_price_per_million=35.50)
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    # Verify input price changed
    assert updated_model.input_price_per_million == 35.50
    # Verify output price unchanged
    assert updated_model.output_price_per_million == 60.0
    # Verify other fields unchanged
    assert updated_model.model_name == "GPT-4"
    assert updated_model.is_active is True


@pytest.mark.asyncio
async def test_inline_update_output_price_only(async_session, test_provider):
    """Test inline updating only output price without changing other fields"""
    # Create model with both prices
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="GPT-3.5 Turbo",
        model_id="gpt-3.5-turbo",
        is_active=True,
        input_price_per_million=0.50,
        output_price_per_million=1.50
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Update only output price (simulating inline editing)
    update_data = ProviderModelUpdate(output_price_per_million=2.00)
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    # Verify output price changed
    assert updated_model.output_price_per_million == 2.00
    # Verify input price unchanged
    assert updated_model.input_price_per_million == 0.50
    # Verify other fields unchanged
    assert updated_model.model_name == "GPT-3.5 Turbo"
    assert updated_model.is_active is True


@pytest.mark.asyncio
async def test_inline_clear_price(async_session, test_provider):
    """Test clearing a price by setting it to None"""
    # Create model with prices
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
    
    # Clear input price (simulating empty input in inline editor)
    update_data = ProviderModelUpdate(input_price_per_million=None)
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    # Verify input price is now None
    assert updated_model.input_price_per_million is None
    # Verify output price unchanged
    assert updated_model.output_price_per_million == 20.0


@pytest.mark.asyncio
async def test_inline_update_preserves_decimal_places(async_session, test_provider):
    """Test that price updates preserve proper decimal precision"""
    # Create model
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="Precision Test",
        model_id="precision-test",
        is_active=True,
        input_price_per_million=0.0,
        output_price_per_million=0.0
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Update with price that should maintain 2 decimal places
    update_data = ProviderModelUpdate(input_price_per_million=10.50)
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    assert updated_model.input_price_per_million == 10.50
    
    # Update with whole number
    update_data = ProviderModelUpdate(output_price_per_million=100.00)
    updated_model = await ProviderService.update_provider_model(
        async_session, model.id, update_data
    )
    await async_session.commit()
    
    assert updated_model.output_price_per_million == 100.00


@pytest.mark.asyncio
async def test_inline_rapid_updates(async_session, test_provider):
    """Test multiple rapid inline price updates (simulating user editing)"""
    # Create model
    model_data = ProviderModelCreate(
        provider_id=test_provider.id,
        model_name="Rapid Update Test",
        model_id="rapid-test",
        is_active=True,
        input_price_per_million=10.0,
        output_price_per_million=20.0
    )
    
    model = await ProviderService.create_provider_model(async_session, model_data)
    await async_session.commit()
    
    # Simulate multiple rapid edits
    prices = [15.0, 20.5, 25.75, 30.00]
    for price in prices:
        update_data = ProviderModelUpdate(input_price_per_million=price)
        updated_model = await ProviderService.update_provider_model(
            async_session, model.id, update_data
        )
        await async_session.commit()
    
    # Verify final price is correct
    final_model = await ProviderService.get_provider_models(async_session, test_provider.id)
    assert final_model[0].input_price_per_million == 30.00
    # Verify output price was never affected
    assert final_model[0].output_price_per_million == 20.0
