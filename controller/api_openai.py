"""
OpenAI API Controller

This controller encapsulates and represents the functions/endpoints of the OpenAI API.
The main task of the controller is to send requests to the OpenAI API and receive and return the response.
"""

import logging
from typing import Optional
import openai
from openai import AsyncOpenAI

from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult
from config import OPENAI_API_KEY, OPENAI_ORG_ID

# Configure logging
logger = logging.getLogger(__name__)


class OpenAIController:
    """Controller for OpenAI API interactions"""
    
    def __init__(self, strict_mode=True, api_key=None, org_id=None):
        """
        Initialize OpenAI client with configuration
        
        Args:
            strict_mode: If True, raises ValueError when API key is missing.
                        If False, allows initialization but requests will fail gracefully.
            api_key: Optional API key to use (if not provided, falls back to environment variable)
            org_id: Optional organization ID to use (if not provided, falls back to environment variable)
        """
        import os
        # Use provided API key or fallback to environment variable
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "") or OPENAI_API_KEY
        self.org_id = org_id or os.environ.get("OPENAI_ORG_ID", "") or OPENAI_ORG_ID
        
        if not self.api_key:
            if strict_mode:
                raise ValueError("OpenAI API key is required but not configured")
            else:
                logger.warning("OpenAI API key is not configured")
                self.client = None
        else:
            # Initialize async OpenAI client
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                organization=self.org_id if self.org_id else None
            )
            logger.info("OpenAI Controller initialized")
    
    async def process_request(self, request: aiapirequest) -> aiapiresult:
        """
        Process an AI API request and return the result
        
        Args:
            request: The aiapirequest object containing job_id, user_id, model, role, and prompt
            
        Returns:
            aiapiresult: The result containing response content, success status, and any error messages
        """
        logger.info(f"Processing OpenAI request for job_id: {request.job_id}, user_id: {request.user_id}")
        
        # Check if OpenAI client is initialized
        if not self.client:
            error_msg = "OpenAI API key is not configured"
            logger.error(f"Configuration error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
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
            
            # Make API call to OpenAI
            logger.debug(f"Sending request to OpenAI API with model: {request.model}")
            
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=0.7,  # Default temperature
                max_tokens=None,  # Let OpenAI decide
            )
            
            # Extract content and token usage from response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content is None:
                    content = ""
                
                # Get token usage if available
                tokens_used = 0
                if hasattr(response, 'usage') and response.usage:
                    tokens_used = response.usage.total_tokens
                    logger.debug(f"Token usage for job_id {request.job_id}: {tokens_used}")
                
                logger.info(f"Successfully received response for job_id: {request.job_id}")
                
                result = aiapiresult(
                    job_id=request.job_id,
                    user_id=request.user_id,
                    content=content,
                    success=True,
                    error_message=None
                )
                # Attach token usage for rate limiting
                result.tokens_used = tokens_used
                return result
            else:
                error_msg = "No response choices returned from OpenAI API"
                logger.error(f"Error for job_id {request.job_id}: {error_msg}")
                
                return aiapiresult(
                    job_id=request.job_id,
                    user_id=request.user_id,
                    content="",
                    success=False,
                    error_message=error_msg
                )
                
        except openai.RateLimitError as e:
            error_msg = f"OpenAI API rate limit exceeded: {str(e)}"
            logger.error(f"Rate limit error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )
            
        except openai.AuthenticationError as e:
            error_msg = f"OpenAI API authentication failed: {str(e)}"
            logger.error(f"Authentication error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )
            
        except openai.APIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(f"API error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )


# Singleton instance
_openai_controller: Optional[OpenAIController] = None


def get_openai_controller(api_key: Optional[str] = None, org_id: Optional[str] = None) -> OpenAIController:
    """
    Get or create the OpenAI controller singleton instance
    
    Args:
        api_key: Optional API key to use for initialization
        org_id: Optional organization ID to use for initialization
        
    Note: If api_key or org_id is provided, a new controller instance will be created
    """
    global _openai_controller
    
    # If api_key or org_id is provided, always create a new instance
    if api_key or org_id:
        return OpenAIController(strict_mode=False, api_key=api_key, org_id=org_id)
    
    # Otherwise use singleton with non-strict mode for production
    if _openai_controller is None:
        _openai_controller = OpenAIController(strict_mode=False)
    return _openai_controller


async def process_openai_request(request: aiapirequest, api_key: Optional[str] = None, org_id: Optional[str] = None) -> aiapiresult:
    """
    Convenience function to process OpenAI requests
    
    Args:
        request: The aiapirequest object
        api_key: Optional API key to use (if not provided, uses environment variable)
        org_id: Optional organization ID to use (if not provided, uses environment variable)
        
    Returns:
        aiapiresult: The processed result
    """
    controller = get_openai_controller(api_key, org_id)
    return await controller.process_request(request)
