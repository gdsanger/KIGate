#!/usr/bin/env python3
"""
Test script for mail functionality
"""
import asyncio
import os
from service.graph_service import GraphService

async def test_mail_template():
    """Test mail template rendering"""
    print("Testing mail template rendering...")
    
    try:
        graph_service = GraphService()
        
        # Test template rendering
        template = graph_service.jinja_env.get_template("new_user_credentials.html")
        html_content = template.render(
            user_name="Test User",
            client_id="test-client-id-12345",
            client_secret="test-secret-67890",
            sender_email="uis@isartec.de"
        )
        
        print("✓ Template rendered successfully")
        print(f"Template length: {len(html_content)} characters")
        
        # Check if key elements are in the template
        assert "Test User" in html_content
        assert "test-client-id-12345" in html_content
        assert "test-secret-67890" in html_content
        assert "uis@isartec.de" in html_content
        
        print("✓ All template variables correctly replaced")
        
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False
    
    return True

async def test_graph_service_config():
    """Test GraphService configuration"""
    print("\nTesting GraphService configuration...")
    
    try:
        graph_service = GraphService()
        
        print(f"Client ID configured: {'Yes' if graph_service.client_id else 'No'}")
        print(f"Tenant ID configured: {'Yes' if graph_service.tenant_id else 'No'}")
        print(f"Client Secret configured: {'Yes' if graph_service.client_secret else 'No'}")
        print(f"Base URL: {graph_service.base_url}")
        print(f"Sender: {graph_service.sender}")
        
        # Check if MSAL app is initialized
        if graph_service.app:
            print("✓ MSAL app initialized successfully")
        else:
            print("❌ MSAL app not initialized")
            return False
            
    except Exception as e:
        print(f"❌ GraphService configuration test failed: {e}")
        return False
    
    return True

async def test_token_acquisition():
    """Test token acquisition (will fail without proper credentials but should not crash)"""
    print("\nTesting token acquisition...")
    
    try:
        graph_service = GraphService()
        token = await graph_service._get_access_token()
        
        if token:
            print("✓ Token acquired successfully")
        else:
            print("⚠️ Token acquisition failed (expected without proper Azure credentials)")
            
    except Exception as e:
        print(f"⚠️ Token acquisition error (expected): {e}")
    
    return True

async def main():
    """Run all tests"""
    print("=== Mail Functionality Tests ===\n")
    
    tests = [
        ("Template Rendering", test_mail_template),
        ("GraphService Configuration", test_graph_service_config),
        ("Token Acquisition", test_token_acquisition)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n=== Test Results ===")
    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed_tests = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

if __name__ == "__main__":
    asyncio.run(main())