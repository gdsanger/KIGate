"""
Request utility functions for extracting client IP and other request data
"""
from typing import Optional
from fastapi import Request


def get_client_ip(request: Request) -> Optional[str]:
    """
    Extract client IP address from request
    Handles X-Forwarded-For header for proxied requests
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Client IP address as string, or None
    """
    # Check X-Forwarded-For header (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first (client)
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header (alternative proxy header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection IP
    if request.client:
        return request.client.host
    
    return None


def extract_auth_token(request: Request) -> Optional[str]:
    """
    Extract authentication token from request
    Supports both Bearer token and API key formats
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Token/API key, or None
    """
    # Check Authorization header for Bearer token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    # Check for API key in query parameters
    # Note: This is handled separately by endpoints, but kept for reference
    return None
