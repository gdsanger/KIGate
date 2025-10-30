"""
Google Gemini API Controller

This controller encapsulates and represents the functions/endpoints of the Google Gemini API.
The main task of the controller is to send requests to the Google Gemini API and receive and return the response.
"""

import logging
from typing import Optional
import google.generativeai as genai

from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult

# Configure logging
logger = logging.getLogger(__name__)


class GeminiController:
    """Controller for Google Gemini API interactions"""
    
    def __init__(self, strict_mode: bool = True, api_key: Optional[str] = None):
        """
        Initialize Gemini controller with API configuration
        
        Args:
            strict_mode: If True, raises error when API key is missing
            api_key: Optional API key to use (if not provided, falls back to environment variable)
        """
        import os
        from config import GEMINI_API_KEY
        self.client = None
        
        # Use provided API key or fallback to environment variable
        effective_api_key = api_key or os.environ.get("GEMINI_API_KEY", "") or GEMINI_API_KEY
        
        if effective_api_key:
            try:
                genai.configure(api_key=effective_api_key)
                # Verify the configuration works
                self.client = genai.GenerativeModel('gemini-pro')
                logger.info("Gemini API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini API client: {str(e)}")
                if strict_mode:
                    raise ValueError(f"Failed to initialize Gemini API client: {str(e)}")
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables or parameters")
            if strict_mode:
                raise ValueError("Gemini API key is not configured")
    
    async def process_request(self, request: aiapirequest) -> aiapiresult:
        """
        Process an AI API request and return the result
        
        Args:
            request: The aiapirequest object containing job_id, user_id, model, and message
            
        Returns:
            aiapiresult: The result containing response content, success status, and any error messages
        """
        # Capture job_id and user_id at entry to prevent any mutation issues during async processing
        job_id = request.job_id
        user_id = request.user_id
        
        logger.info(f"Processing Gemini request for job_id: {job_id}, user_id: {user_id}")
        
        # Check if Gemini client is initialized
        if not self.client:
            error_msg = "Gemini API key is not configured"
            logger.error(f"Configuration error for job_id {job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=job_id,
                user_id=user_id,
                content="",
                success=False,
                error_message=error_msg
            )
        
        try:
            # Validate input parameters
            if not request.message or not request.message.strip():
                raise ValueError("Message cannot be empty")
            
            if not request.model or not request.model.strip():
                raise ValueError("Model cannot be empty")
            
            # Create generative model with specified model or default to gemini-pro
            try:
                model = genai.GenerativeModel(request.model)
            except Exception as e:
                logger.warning(f"Failed to use model '{request.model}', falling back to 'gemini-pro': {str(e)}")
                model = genai.GenerativeModel('gemini-pro')
            
            # Make API call to Gemini
            logger.debug(f"Sending request to Gemini API with model: {request.model}")
            
            response = model.generate_content(request.message)
            
            # Extract content and token usage from response
            if response and response.text:
                content = response.text
                
                # Get token usage if available
                tokens_used = 0
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    tokens_used = response.usage_metadata.total_token_count
                    logger.debug(f"Token usage for job_id {job_id}: {tokens_used}")
                
                logger.info(f"Successfully received response for job_id: {job_id}")
                
                result = aiapiresult(
                    job_id=job_id,
                    user_id=user_id,
                    content=content,
                    success=True,
                    error_message=None
                )
                result.tokens_used = tokens_used
                return result
            else:
                error_msg = "No response text returned from Gemini API"
                logger.error(f"Error for job_id {job_id}: {error_msg}")
                
                return aiapiresult(
                    job_id=job_id,
                    user_id=user_id,
                    content="",
                    success=False,
                    error_message=error_msg
                )
                
        except ValueError as e:
            # Validation errors
            error_msg = f"Validation error: {str(e)}"
            logger.error(f"Validation error for job_id {job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=job_id,
                user_id=user_id,
                content="",
                success=False,
                error_message=error_msg
            )
        
        except Exception as e:
            # Check for specific Gemini API errors
            error_str = str(e).lower()
            
            if "quota" in error_str or "limit" in error_str:
                error_msg = f"Rate limit or quota exceeded: {str(e)}"
                logger.error(f"Rate limit error for job_id {job_id}: {error_msg}")
            elif "permission" in error_str or "unauthorized" in error_str or "forbidden" in error_str:
                error_msg = f"Authentication error: {str(e)}"
                logger.error(f"Authentication error for job_id {job_id}: {error_msg}")
            elif "api" in error_str:
                error_msg = f"Gemini API error: {str(e)}"
                logger.error(f"API error for job_id {job_id}: {error_msg}")
            else:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error for job_id {job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=job_id,
                user_id=user_id,
                content="",
                success=False,
                error_message=error_msg
            )


# Singleton instance
_gemini_controller: Optional[GeminiController] = None


def get_gemini_controller(api_key: Optional[str] = None) -> GeminiController:
    """
    Get or create the Gemini controller singleton instance
    
    Args:
        api_key: Optional API key to use for initialization
        
    Note: If api_key is provided, a new controller instance will be created
    """
    global _gemini_controller
    
    # If api_key is provided, always create a new instance
    if api_key:
        return GeminiController(strict_mode=False, api_key=api_key)
    
    # Otherwise use singleton
    if _gemini_controller is None:
        _gemini_controller = GeminiController(strict_mode=False)
    return _gemini_controller


async def process_gemini_request(request: aiapirequest, api_key: Optional[str] = None) -> aiapiresult:
    """
    Process a Gemini API request using the controller
    
    Args:
        request: The aiapirequest object
        api_key: Optional API key to use (if not provided, uses environment variable)
        
    Returns:
        aiapiresult: The response from Gemini API
    """
    controller = get_gemini_controller(api_key)
    return await controller.process_request(request)