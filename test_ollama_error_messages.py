"""
Test to verify error message improvements for missing Ollama dependency
"""
import pytest
from unittest.mock import patch, AsyncMock
from model.aiapirequest import aiapirequest
from service.ai_service import send_ai_request


@pytest.mark.asyncio
async def test_ollama_import_error_message():
    """Test that error message helper provides useful guidance"""
    from utils.dependency_checker import DependencyChecker
    
    # Simulate what happens in ai_service when an ImportError occurs
    error = ImportError("No module named 'ollama'")
    
    # Get the help message
    help_msg = DependencyChecker.get_installation_help_message('ollama')
    
    # Construct the error message as ai_service would
    error_msg = f"Provider ollama controller not available: {str(error)}. {help_msg}"
    
    # Verify the error message is helpful
    assert "No module named 'ollama'" in error_msg
    assert "pip install" in error_msg.lower()
    assert "requirements.txt" in error_msg
    assert "ollama" in error_msg.lower()


@pytest.mark.asyncio
async def test_error_message_contains_help():
    """Test that error messages contain installation help"""
    from utils.dependency_checker import DependencyChecker
    
    # Test that we get helpful messages for each provider
    help_msg_ollama = DependencyChecker.get_installation_help_message('ollama')
    assert 'ollama' in help_msg_ollama.lower()
    assert 'pip install' in help_msg_ollama.lower()
    assert 'requirements.txt' in help_msg_ollama
    
    help_msg_openai = DependencyChecker.get_installation_help_message('openai')
    assert 'openai' in help_msg_openai.lower()
    assert 'pip install' in help_msg_openai.lower()
    
    help_msg_generic = DependencyChecker.get_installation_help_message()
    assert 'pip install' in help_msg_generic.lower()
    assert 'requirements.txt' in help_msg_generic


@pytest.mark.asyncio
async def test_dependency_check_warns_for_missing_provider():
    """Test that dependency checker warns about missing provider dependencies"""
    from utils.dependency_checker import DependencyChecker
    import logging
    
    # This test verifies the behavior when a provider dependency is missing
    # We can't actually remove packages, but we can verify the checker works
    
    # Mock check_package to simulate missing ollama
    with patch.object(DependencyChecker, 'check_package') as mock_check:
        def side_effect(package_name):
            if package_name == 'ollama':
                return False
            return True
        
        mock_check.side_effect = side_effect
        
        # Check provider dependencies
        results = DependencyChecker.check_provider_dependencies()
        
        # Ollama should show as not installed
        assert results['ollama']['ollama'] is False
        
        # Verify all dependencies
        all_core, missing_providers = DependencyChecker.verify_all_dependencies()
        
        # Should report ollama as missing
        assert 'ollama' in missing_providers


@pytest.mark.asyncio  
async def test_startup_fails_with_missing_core_deps():
    """Test that startup check fails when core dependencies are missing"""
    from utils.dependency_checker import DependencyChecker
    
    # Mock check_package to simulate missing fastapi
    with patch.object(DependencyChecker, 'check_package') as mock_check:
        def side_effect(package_name):
            if package_name == 'fastapi':
                return False
            return True
        
        mock_check.side_effect = side_effect
        
        # Verify all dependencies - should fail
        all_core, missing_providers = DependencyChecker.verify_all_dependencies()
        
        # Core should not be fully installed
        assert all_core is False
