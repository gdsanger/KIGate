"""
Ollama API Controller

This controller encapsulates and represents the functions/endpoints of the Ollama API.
The main task of the controller is to send requests to the Ollama API and receive and return the response.
"""

import logging
from typing import Optional
from ollama import AsyncClient

from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult

# Configure logging
logger = logging.getLogger(__name__)


class OllamaController:
    """Controller for Ollama API interactions"""
    
    def __init__(self, strict_mode=True, api_url=None):
        """
        Initialize Ollama client with configuration
        
        Args:
            strict_mode: If True, raises ValueError when API URL is missing.
                        If False, allows initialization but requests will fail gracefully.
            api_url: Optional API URL to use (e.g., http://localhost:11434)
        """
        self.api_url = api_url
        
        if not self.api_url:
            if strict_mode:
                raise ValueError("Ollama API URL is required but not configured")
            else:
                logger.warning("Ollama API URL is not configured")
                self.client = None
        else:
            # Initialize async Ollama client with custom host
            try:
                self.client = AsyncClient(host=self.api_url)
                logger.info(f"Ollama Controller initialized with URL: {self.api_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama client: {str(e)}")
                if strict_mode:
                    raise
                self.client = None
    
    async def process_request(self, request: aiapirequest) -> aiapiresult:
        """
        Process an AI API request and return the result
        
        Args:
            request: The aiapirequest object containing job_id, user_id, model, role, and prompt
            
        Returns:
            aiapiresult: The result containing response content, success status, and any error messages
        """
        # Capture job_id and user_id at entry to prevent any mutation issues during async processing
        job_id = request.job_id
        user_id = request.user_id
        
        logger.info(f"Processing Ollama request for job_id: {job_id}, user_id: {user_id}")
        
        # Check if Ollama client is initialized
        if not self.client:
            error_msg = "Ollama API URL is not configured"
            logger.error(f"Configuration error for job_id {job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=job_id,
                user_id=user_id,
                content="",
                success=False,
                error_message=error_msg
            )
        
        try:
            # Validate input parameters and determine content/role
            content = None
            role = "user"  # default role
            
            # Support both patterns: message field OR prompt/role fields
            if request.message:
                content = request.message
                # Use default role "user" when using message field
            elif request.prompt:
                content = request.prompt
                if request.role and request.role.strip():
                    role = request.role
            else:
                raise ValueError("Either 'message' or 'prompt' field must be provided")
            
            if not content or not content.strip():
                raise ValueError("Content cannot be empty")
            
            if not request.model or not request.model.strip():
                raise ValueError("Model cannot be empty")
            
            # Prepare the message based on role and content
            messages = []
            if role.lower() in ['system', 'user', 'assistant']:
                messages.append({
                    "role": role.lower(),
                    "content": content
                })
            else:
                # Default to user role if role is invalid
                logger.warning(f"Invalid role '{role}', defaulting to 'user'")
                messages.append({
                    "role": "user",
                    "content": content
                })
            
            # Make API call to Ollama
            logger.debug(f"Sending request to Ollama API with model: {request.model}")
            
            response = await self.client.chat(
                model=request.model,
                messages=messages,
                stream=False
            )
            
            # Extract content from response
            if response and hasattr(response, 'message') and response.message:
                content = response.message.content if hasattr(response.message, 'content') else str(response.message)
                if content is None:
                    content = ""
                
                logger.info(f"Successfully received response for job_id: {job_id}")
                
                return aiapiresult(
                    job_id=job_id,
                    user_id=user_id,
                    content=content,
                    success=True,
                    error_message=None
                )
            else:
                error_msg = "No response message returned from Ollama API"
                logger.error(f"Error for job_id {job_id}: {error_msg}")
                
                return aiapiresult(
                    job_id=job_id,
                    user_id=user_id,
                    content="",
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
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
_ollama_controller: Optional[OllamaController] = None


def get_ollama_controller(api_url: Optional[str] = None) -> OllamaController:
    """
    Get or create the Ollama controller singleton instance
    
    Args:
        api_url: Optional API URL to use for initialization
        
    Note: If api_url is provided, a new controller instance will be created
    """
    global _ollama_controller
    
    # If api_url is provided, always create a new instance
    if api_url:
        return OllamaController(strict_mode=False, api_url=api_url)
    
    # Otherwise use singleton with non-strict mode for production
    if _ollama_controller is None:
        _ollama_controller = OllamaController(strict_mode=False)
    return _ollama_controller


async def process_ollama_request(request: aiapirequest, api_url: Optional[str] = None) -> aiapiresult:
    """
    Convenience function to process Ollama requests
    
    Args:
        request: The aiapirequest object
        api_url: Optional API URL to use (e.g., http://localhost:11434)
        
    Returns:
        aiapiresult: The processed result
    """
    controller = get_ollama_controller(api_url)
    return await controller.process_request(request)
