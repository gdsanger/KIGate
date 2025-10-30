"""
AI Service for routing requests to different AI providers
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult

logger = logging.getLogger(__name__)


async def send_ai_request(request: aiapirequest, provider: str, db: Optional[AsyncSession] = None) -> aiapiresult:
    """
    Send AI request to the specified provider
    
    Args:
        request: The aiapirequest object
        provider: Provider name (openai, claude, gemini, etc.)
        db: Optional database session to fetch provider configuration
        
    Returns:
        aiapiresult: The result from the AI provider
    """
    # Normalize provider name to handle variations
    # Map common provider display names to their canonical lowercase identifiers
    provider_mapping = {
        "google gemini": "gemini",
        "gemini": "gemini",
        "openai": "openai",
        "claude": "claude",
        "anthropic claude": "claude",
        "ollama": "ollama",
        "ollama (local)": "ollama",
        "ollama (loakl)": "ollama",  # Handle typo
    }
    
    # Normalize: lowercase and strip whitespace
    normalized_provider = provider.lower().strip()
    
    # Check if it matches any known mapping
    canonical_provider = provider_mapping.get(normalized_provider, normalized_provider)
    
    # Log the provider mapping if a transformation occurred
    if canonical_provider != provider:
        logger.info(f"Normalized provider '{provider}' to '{canonical_provider}'")
    
    logger.info(f"Routing AI request to provider: {canonical_provider}")
    
    # Fetch provider configuration from database if db session is provided
    api_key = None
    org_id = None
    api_url = None
    
    if db:
        try:
            from service.provider_service import ProviderService
            from sqlalchemy import select
            from model.provider import Provider
            
            # Find active provider by provider_type
            result = await db.execute(
                select(Provider).where(
                    Provider.provider_type == canonical_provider,
                    Provider.is_active == True
                )
            )
            provider_entity = result.scalar_one_or_none()
            
            if provider_entity:
                api_key = provider_entity.api_key
                org_id = provider_entity.organization_id
                api_url = provider_entity.api_url
                logger.info(f"Using provider configuration from database for '{canonical_provider}' (ID: {provider_entity.id})")
            else:
                logger.warning(f"No active provider found in database for type '{canonical_provider}', falling back to environment variables")
        except Exception as e:
            logger.warning(f"Error fetching provider from database: {str(e)}, falling back to environment variables")
    
    try:
        if canonical_provider == "openai":
            from controller.api_openai import process_openai_request
            return await process_openai_request(request, api_key=api_key, org_id=org_id)
        
        elif canonical_provider == "claude":
            from controller.api_claude import process_claude_request
            return await process_claude_request(request, api_key=api_key)
        
        elif canonical_provider == "gemini":
            from controller.api_gemini import process_gemini_request
            return await process_gemini_request(request, api_key=api_key)
        
        elif canonical_provider == "ollama":
            from controller.api_ollama import process_ollama_request
            return await process_ollama_request(request, api_url=api_url)
        
        else:
            # Unsupported provider
            error_msg = f"Unsupported AI provider: {provider} (normalized to: {canonical_provider})"
            logger.error(f"Error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )
            
    except ImportError as e:
        from utils.dependency_checker import DependencyChecker
        help_msg = DependencyChecker.get_installation_help_message(canonical_provider)
        error_msg = f"Provider {provider} controller not available: {str(e)}. {help_msg}"
        logger.error(f"Import error for job_id {request.job_id}: {error_msg}")
        
        return aiapiresult(
            job_id=request.job_id,
            user_id=request.user_id,
            content="",
            success=False,
            error_message=error_msg
        )
    
    except Exception as e:
        error_msg = f"Error processing request with provider {provider}: {str(e)}"
        logger.error(f"Unexpected error for job_id {request.job_id}: {error_msg}")
        
        return aiapiresult(
            job_id=request.job_id,
            user_id=request.user_id,
            content="",
            success=False,
            error_message=error_msg
        )