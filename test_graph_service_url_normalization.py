#!/usr/bin/env python3
"""
Test script for GraphService URL normalization to fix duplicate /v1.0 segments
"""
import os
import sys
from service.graph_service import GraphService
import config

def test_base_url_normalization():
    """Test that base URLs are properly normalized to avoid duplicate /v1.0 segments"""
    print("Testing base URL normalization...")
    
    service = GraphService()
    
    test_cases = [
        # Standard case
        ("https://graph.microsoft.com", "https://graph.microsoft.com"),
        # With trailing slash
        ("https://graph.microsoft.com/", "https://graph.microsoft.com"),
        # With /v1.0 suffix (problematic case)
        ("https://graph.microsoft.com/v1.0", "https://graph.microsoft.com"),
        # With /v1.0/ suffix
        ("https://graph.microsoft.com/v1.0/", "https://graph.microsoft.com"),
        # Custom endpoint
        ("https://custom.endpoint.com", "https://custom.endpoint.com"),
        # Custom endpoint with /v1.0
        ("https://custom.endpoint.com/v1.0", "https://custom.endpoint.com")
    ]
    
    all_passed = True
    for i, (input_url, expected) in enumerate(test_cases, 1):
        result = service._normalize_base_url(input_url)
        passed = result == expected
        
        if not passed:
            print(f"❌ Test {i} FAILED: input='{input_url}', expected='{expected}', got='{result}'")
            all_passed = False
        else:
            print(f"✓ Test {i} passed: '{input_url}' -> '{result}'")
    
    return all_passed

def test_email_url_construction():
    """Test that email URLs are constructed correctly without duplicate /v1.0 segments"""
    print("\nTesting email URL construction...")
    
    # Store original config
    original_base_url = config.BaseUrl
    sender = "test@example.com"
    expected_url = "https://graph.microsoft.com/v1.0/users/test@example.com/sendMail"
    
    problematic_configs = [
        "https://graph.microsoft.com/v1.0",
        "https://graph.microsoft.com/v1.0/",
    ]
    
    all_passed = True
    
    try:
        for i, base_url in enumerate(problematic_configs, 1):
            # Temporarily set config to problematic value
            config.BaseUrl = base_url
            
            # Create new service instance
            service = GraphService()
            
            # Construct URL as done in send_email method
            constructed_url = f"{service.base_url}/v1.0/users/{sender}/sendMail"
            
            passed = constructed_url == expected_url
            if not passed:
                print(f"❌ Test {i} FAILED: config='{base_url}', expected='{expected_url}', got='{constructed_url}'")
                all_passed = False
            else:
                print(f"✓ Test {i} passed: config='{base_url}' -> '{constructed_url}'")
    
    finally:
        # Restore original config
        config.BaseUrl = original_base_url
    
    return all_passed

async def main():
    """Run URL normalization tests"""
    print("=== GraphService URL Normalization Tests ===\n")
    
    test1_passed = test_base_url_normalization()
    test2_passed = test_email_url_construction()
    
    print(f"\n=== Test Results ===")
    print(f"Base URL normalization: {'✓ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Email URL construction: {'✓ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n✓ All URL normalization tests passed!")
        print("The fix prevents duplicate /v1.0 segments in Graph API URLs.")
        return True
    else:
        print("\n❌ Some URL normalization tests failed!")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())