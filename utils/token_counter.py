"""
Utility functions for token counting
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global tiktoken encoding instances
_encodings = {}


def get_encoding_for_model(model: str):
    """Get the appropriate tiktoken encoding for a model"""
    try:
        import tiktoken
        
        if model in _encodings:
            return _encodings[model]
        
        # Try to get encoding for the specific model
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models (used by GPT-4, GPT-3.5-turbo)
            logger.warning(f"Unknown model {model}, using cl100k_base encoding")
            encoding = tiktoken.get_encoding("cl100k_base")
        
        _encodings[model] = encoding
        return encoding
    except ImportError:
        logger.warning("tiktoken not available, token counting disabled")
        return None
    except Exception as e:
        logger.error(f"Error getting encoding for model {model}: {str(e)}")
        return None


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> Optional[int]:
    """
    Count tokens in text using tiktoken
    
    Args:
        text: The text to count tokens for
        model: The model name to determine encoding
        
    Returns:
        Number of tokens, or None if counting fails
    """
    if not text:
        return 0
    
    try:
        encoding = get_encoding_for_model(model)
        if not encoding:
            return None
        
        tokens = encoding.encode(text)
        return len(tokens)
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        return None


def count_message_tokens(messages: list, model: str = "gpt-3.5-turbo") -> Optional[int]:
    """
    Count tokens in a list of messages (OpenAI format)
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: The model name to determine encoding
        
    Returns:
        Number of tokens, or None if counting fails
    """
    try:
        encoding = get_encoding_for_model(model)
        if not encoding:
            return None
        
        num_tokens = 0
        
        # Account for message formatting tokens
        for message in messages:
            num_tokens += 4  # Every message has 4 tokens overhead
            for key, value in message.items():
                if isinstance(value, str):
                    num_tokens += len(encoding.encode(value))
        
        num_tokens += 2  # Every reply is primed with 2 tokens
        
        return num_tokens
    except Exception as e:
        logger.error(f"Error counting message tokens: {str(e)}")
        return None
