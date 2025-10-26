"""
AI Service for routing requests to different AI providers
"""
import logging
from typing import Optional
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult

logger = logging.getLogger(__name__)


async def send_ai_request(request: aiapirequest, provider: str) -> aiapiresult:
    """
    Send AI request to the specified provider
    
    Args:
        request: The aiapirequest object
        provider: Provider name (openai, claude, gemini, etc.)
        
    Returns:
        aiapiresult: The result from the AI provider
    """
    logger.info(f"Routing AI request to provider: {provider}")
    
    try:
        if provider.lower() == "openai":
            from controller.api_openai import process_openai_request
            return await process_openai_request(request)
        
        elif provider.lower() == "claude":
            from controller.api_claude import process_claude_request
            return await process_claude_request(request)
        
        elif provider.lower() == "gemini":
            from controller.api_gemini import process_gemini_request
            return await process_gemini_request(request)
        
        else:
            # Unsupported provider
            error_msg = f"Unsupported AI provider: {provider}"
            logger.error(f"Error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )
            
    except ImportError as e:
        error_msg = f"Provider {provider} controller not available: {str(e)}"
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