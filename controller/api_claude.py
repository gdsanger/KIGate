"""
Claude API Controller

This controller encapsulates and represents the functions/endpoints of the Claude API.
The main task of the controller is to send requests to the Claude API and receive and return the response.
"""

import logging
from typing import Optional
import anthropic
from anthropic import AsyncAnthropic

from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult
from config import ANTHROPIC_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MAX_TOKENS = 1000  # Default max tokens for Claude responses


class ClaudeController:
    """Controller for Claude API interactions"""
    
    def __init__(self, strict_mode=True, api_key=None):
        """
        Initialize Claude client with configuration
        
        Args:
            strict_mode: If True, raises ValueError when API key is missing.
                        If False, allows initialization but requests will fail gracefully.
            api_key: Override API key (defaults to config value)
        """
        import os
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "") or ANTHROPIC_API_KEY
        
        if not self.api_key:
            if strict_mode:
                raise ValueError("Anthropic API key is required but not configured")
            else:
                logger.warning("Anthropic API key is not configured")
                self.client = None
        else:
            # Initialize async Anthropic client
            self.client = AsyncAnthropic(
                api_key=self.api_key
            )
            logger.info("Claude Controller initialized")
    
    async def process_request(self, request: aiapirequest) -> aiapiresult:
        """
        Process an AI API request and return the result
        
        Args:
            request: The aiapirequest object containing job_id, user_id, model, and message
            
        Returns:
            aiapiresult: The result containing response content, success status, and any error messages
        """
        logger.info(f"Processing Claude request for job_id: {request.job_id}, user_id: {request.user_id}")
        
        try:
            # Validate input parameters first (before checking API configuration)
            if not request.message or not request.message.strip():
                raise ValueError("Message cannot be empty")
            
            if not request.model or not request.model.strip():
                raise ValueError("Model cannot be empty")
            
            # Check if Claude client is initialized
            if not self.client:
                error_msg = "Anthropic API key is not configured"
                logger.error(f"Configuration error for job_id {request.job_id}: {error_msg}")
                
                return aiapiresult(
                    job_id=request.job_id,
                    user_id=request.user_id,
                    content="",
                    success=False,
                    error_message=error_msg
                )
            
            # Make API call to Claude
            logger.debug(f"Sending request to Claude API with model: {request.model}")
            
            response = await self.client.messages.create(
                model=request.model,
                max_tokens=DEFAULT_MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": request.message
                    }
                ]
            )
            
            # Extract content and token usage from response
            if response.content and len(response.content) > 0:
                content = response.content[0].text
                if content is None:
                    content = ""
                
                # Get token usage if available
                tokens_used = 0
                if hasattr(response, 'usage') and response.usage:
                    tokens_used = response.usage.input_tokens + response.usage.output_tokens
                    logger.debug(f"Token usage for job_id {request.job_id}: {tokens_used}")
                
                logger.info(f"Successfully received response for job_id: {request.job_id}")
                
                result = aiapiresult(
                    job_id=request.job_id,
                    user_id=request.user_id,
                    content=content,
                    success=True,
                    error_message=None
                )
                result.tokens_used = tokens_used
                return result
            else:
                error_msg = "No response content returned from Claude API"
                logger.error(f"Error for job_id {request.job_id}: {error_msg}")
                
                return aiapiresult(
                    job_id=request.job_id,
                    user_id=request.user_id,
                    content="",
                    success=False,
                    error_message=error_msg
                )
                
        except anthropic.RateLimitError as e:
            error_msg = f"Claude API rate limit exceeded: {str(e)}"
            logger.error(f"Rate limit error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )
            
        except anthropic.AuthenticationError as e:
            error_msg = f"Claude API authentication failed: {str(e)}"
            logger.error(f"Authentication error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )
            
        except anthropic.APIError as e:
            error_msg = f"Claude API error: {str(e)}"
            logger.error(f"API error for job_id {request.job_id}: {error_msg}")
            
            return aiapiresult(
                job_id=request.job_id,
                user_id=request.user_id,
                content="",
                success=False,
                error_message=error_msg
            )
            
        except ValueError as e:
            error_msg = str(e)
            logger.error(f"Validation error for job_id {request.job_id}: {error_msg}")
            
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
_claude_controller: Optional[ClaudeController] = None


def get_claude_controller() -> ClaudeController:
    """Get or create the Claude controller singleton instance"""
    global _claude_controller
    if _claude_controller is None:
        # Use non-strict mode for production to handle missing API keys gracefully
        _claude_controller = ClaudeController(strict_mode=False)
    return _claude_controller


async def process_claude_request(request: aiapirequest) -> aiapiresult:
    """
    Convenience function to process Claude requests
    
    Args:
        request: The aiapirequest object
        
    Returns:
        aiapiresult: The processed result
    """
    controller = get_claude_controller()
    return await controller.process_request(request)