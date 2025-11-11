"""
Provider service for managing AI providers and their models
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from model.provider import (
    Provider, ProviderModel, 
    ProviderCreate, ProviderUpdate, ProviderResponse, 
    ProviderModelCreate, ProviderModelUpdate, ProviderModelResponse,
    ProviderWithModels
)

logger = logging.getLogger(__name__)


class ProviderService:
    """Service for managing AI providers"""

    @staticmethod
    async def get_all_providers(db: AsyncSession, include_models: bool = False) -> List[ProviderWithModels]:
        """Get all providers"""
        query = select(Provider)
        if include_models:
            query = query.options(selectinload(Provider.models))
        
        result = await db.execute(query)
        providers = result.scalars().all()
        
        if include_models:
            return [ProviderWithModels.model_validate(p) for p in providers]
        return [ProviderResponse.model_validate(p) for p in providers]

    @staticmethod
    async def get_provider(db: AsyncSession, provider_id: str, include_models: bool = False) -> Optional[ProviderWithModels]:
        """Get a specific provider by ID"""
        query = select(Provider).where(Provider.id == provider_id)
        if include_models:
            query = query.options(selectinload(Provider.models))
        
        result = await db.execute(query)
        provider = result.scalar_one_or_none()
        
        if provider:
            if include_models:
                return ProviderWithModels.model_validate(provider)
            return ProviderResponse.model_validate(provider)
        return None

    @staticmethod
    async def get_provider_by_name(db: AsyncSession, name: str, include_models: bool = False) -> Optional[ProviderWithModels]:
        """Get a specific provider by name"""
        query = select(Provider).where(Provider.name == name)
        if include_models:
            query = query.options(selectinload(Provider.models))
        
        result = await db.execute(query)
        provider = result.scalar_one_or_none()
        
        if provider:
            if include_models:
                return ProviderWithModels.model_validate(provider)
            return ProviderResponse.model_validate(provider)
        return None

    @staticmethod
    async def create_provider(db: AsyncSession, provider_data: ProviderCreate) -> ProviderResponse:
        """Create a new provider"""
        provider = Provider(
            name=provider_data.name,
            provider_type=provider_data.provider_type,
            api_key=provider_data.api_key,
            api_url=provider_data.api_url,
            organization_id=provider_data.organization_id,
            is_active=provider_data.is_active
        )
        
        db.add(provider)
        await db.flush()
        await db.refresh(provider)
        
        return ProviderResponse.model_validate(provider)

    @staticmethod
    async def update_provider(db: AsyncSession, provider_id: str, provider_data: ProviderUpdate) -> Optional[ProviderResponse]:
        """Update an existing provider"""
        result = await db.execute(select(Provider).where(Provider.id == provider_id))
        provider = result.scalar_one_or_none()
        
        if not provider:
            return None
        
        update_dict = provider_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(provider, key, value)
        
        await db.flush()
        await db.refresh(provider)
        
        return ProviderResponse.model_validate(provider)

    @staticmethod
    async def delete_provider(db: AsyncSession, provider_id: str) -> bool:
        """Delete a provider"""
        result = await db.execute(select(Provider).where(Provider.id == provider_id))
        provider = result.scalar_one_or_none()
        
        if provider:
            await db.delete(provider)
            await db.flush()
            return True
        
        return False

    @staticmethod
    async def get_provider_models(db: AsyncSession, provider_id: str, active_only: bool = False) -> List[ProviderModelResponse]:
        """Get all models for a provider"""
        query = select(ProviderModel).where(ProviderModel.provider_id == provider_id)
        if active_only:
            query = query.where(ProviderModel.is_active == True)
        
        result = await db.execute(query)
        models = result.scalars().all()
        
        return [ProviderModelResponse.model_validate(m) for m in models]

    @staticmethod
    async def create_provider_model(db: AsyncSession, model_data: ProviderModelCreate) -> ProviderModelResponse:
        """Create a new provider model"""
        model = ProviderModel(
            provider_id=model_data.provider_id,
            model_name=model_data.model_name,
            model_id=model_data.model_id,
            is_active=model_data.is_active,
            input_price_per_million=model_data.input_price_per_million,
            output_price_per_million=model_data.output_price_per_million
        )
        
        db.add(model)
        await db.flush()
        await db.refresh(model)
        
        return ProviderModelResponse.model_validate(model)

    @staticmethod
    async def update_provider_model(db: AsyncSession, model_id: str, model_data: ProviderModelUpdate) -> Optional[ProviderModelResponse]:
        """Update an existing provider model"""
        result = await db.execute(select(ProviderModel).where(ProviderModel.id == model_id))
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        update_dict = model_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(model, key, value)
        
        await db.flush()
        await db.refresh(model)
        
        return ProviderModelResponse.model_validate(model)

    @staticmethod
    async def delete_provider_model(db: AsyncSession, model_id: str) -> bool:
        """Delete a provider model"""
        result = await db.execute(select(ProviderModel).where(ProviderModel.id == model_id))
        model = result.scalar_one_or_none()
        
        if model:
            await db.delete(model)
            await db.flush()
            return True
        
        return False

    @staticmethod
    async def fetch_models_from_api(db: AsyncSession, provider_id: str) -> List[ProviderModelResponse]:
        """Fetch available models from provider API and sync to database"""
        provider_result = await db.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        provider = provider_result.scalar_one_or_none()
        
        if not provider:
            raise ValueError(f"Provider with ID {provider_id} not found")
        
        if not provider.is_active:
            raise ValueError(f"Provider {provider.name} is not active")
        
        try:
            models_data = await ProviderService._fetch_models_by_type(provider)
            
            # Get existing models
            existing_models_result = await db.execute(
                select(ProviderModel).where(ProviderModel.provider_id == provider_id)
            )
            existing_models = existing_models_result.scalars().all()
            existing_model_ids = {m.model_id for m in existing_models}
            
            # Add new models
            created_models = []
            for model_data in models_data:
                if model_data['id'] not in existing_model_ids:
                    model = ProviderModel(
                        provider_id=provider_id,
                        model_name=model_data['name'],
                        model_id=model_data['id'],
                        is_active=True
                    )
                    db.add(model)
                    created_models.append(model)
            
            await db.flush()
            
            # Refresh and return all models
            all_models_result = await db.execute(
                select(ProviderModel).where(ProviderModel.provider_id == provider_id)
            )
            all_models = all_models_result.scalars().all()
            
            return [ProviderModelResponse.model_validate(m) for m in all_models]
            
        except Exception as e:
            logger.error(f"Error fetching models from provider {provider.name}: {str(e)}")
            raise

    @staticmethod
    async def _fetch_models_by_type(provider: Provider) -> List[Dict[str, str]]:
        """Fetch models from specific provider type"""
        if provider.provider_type == "openai":
            return await ProviderService._fetch_openai_models(provider)
        elif provider.provider_type == "gemini":
            return await ProviderService._fetch_gemini_models(provider)
        elif provider.provider_type == "claude":
            return await ProviderService._fetch_claude_models(provider)
        elif provider.provider_type == "ollama":
            return await ProviderService._fetch_ollama_models(provider)
        else:
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")

    @staticmethod
    async def _fetch_openai_models(provider: Provider) -> List[Dict[str, str]]:
        """Fetch models from OpenAI API"""
        from openai import AsyncOpenAI
        
        if not provider.api_key:
            raise ValueError("OpenAI API key is required")
        
        client = AsyncOpenAI(
            api_key=provider.api_key,
            organization=provider.organization_id if provider.organization_id else None
        )
        
        models_response = await client.models.list()
        
        # Filter for chat models
        models = []
        for model in models_response.data:
            model_id = model.id
            # Include GPT models and other chat-capable models
            if any(prefix in model_id for prefix in ['gpt-', 'o1-', 'chatgpt-']):
                models.append({
                    'id': model_id,
                    'name': model_id
                })
        
        return sorted(models, key=lambda x: x['id'])

    @staticmethod
    async def _fetch_gemini_models(provider: Provider) -> List[Dict[str, str]]:
        """Fetch models from Google Gemini API"""
        import google.generativeai as genai
        
        if not provider.api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=provider.api_key)
        
        models = []
        for model in genai.list_models():
            # Only include models that support generateContent
            if 'generateContent' in model.supported_generation_methods:
                models.append({
                    'id': model.name.replace('models/', ''),
                    'name': model.name.replace('models/', '')
                })
        
        return models

    @staticmethod
    async def _fetch_claude_models(provider: Provider) -> List[Dict[str, str]]:
        """Fetch models from Claude API"""
        # Claude doesn't have a models list endpoint, so we return known models
        models = [
            {'id': 'claude-3-5-sonnet-20241022', 'name': 'Claude 3.5 Sonnet'},
            {'id': 'claude-3-5-haiku-20241022', 'name': 'Claude 3.5 Haiku'},
            {'id': 'claude-3-opus-20240229', 'name': 'Claude 3 Opus'},
            {'id': 'claude-3-sonnet-20240229', 'name': 'Claude 3 Sonnet'},
            {'id': 'claude-3-haiku-20240307', 'name': 'Claude 3 Haiku'},
        ]
        
        return models

    @staticmethod
    async def _fetch_ollama_models(provider: Provider) -> List[Dict[str, str]]:
        """Fetch models from Ollama API"""
        import httpx
        
        if not provider.api_url:
            raise ValueError("Ollama API URL is required")
        
        # Ensure URL ends with /api/tags
        api_url = provider.api_url.rstrip('/')
        if not api_url.endswith('/api'):
            api_url = f"{api_url}/api"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/tags", timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            if 'models' in data:
                for model in data['models']:
                    model_name = model.get('name', '')
                    models.append({
                        'id': model_name,
                        'name': model_name
                    })
            
            return models
