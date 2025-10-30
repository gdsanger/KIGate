"""
Tests for dependency checker utility
"""
import pytest
from utils.dependency_checker import DependencyChecker


def test_check_package_installed():
    """Test that check_package returns True for installed packages"""
    # Test with a package we know is installed
    assert DependencyChecker.check_package('logging') is True
    assert DependencyChecker.check_package('sys') is True


def test_check_package_not_installed():
    """Test that check_package returns False for non-existent packages"""
    # Test with a package that definitely doesn't exist
    assert DependencyChecker.check_package('this_package_definitely_does_not_exist_12345') is False


def test_check_core_dependencies():
    """Test checking core dependencies"""
    results = DependencyChecker.check_core_dependencies()
    
    # Should return a dict
    assert isinstance(results, dict)
    
    # Should have entries for core dependencies
    assert 'fastapi' in results
    assert 'sqlalchemy' in results
    assert 'uvicorn' in results
    assert 'pydantic' in results
    
    # All should be installed in our test environment
    assert results['fastapi'] is True
    assert results['sqlalchemy'] is True
    assert results['uvicorn'] is True
    assert results['pydantic'] is True


def test_check_provider_dependencies():
    """Test checking provider-specific dependencies"""
    results = DependencyChecker.check_provider_dependencies()
    
    # Should return a dict
    assert isinstance(results, dict)
    
    # Should have entries for all providers
    assert 'openai' in results
    assert 'claude' in results
    assert 'gemini' in results
    assert 'ollama' in results
    
    # Each provider should have package status
    assert isinstance(results['openai'], dict)
    assert isinstance(results['claude'], dict)
    assert isinstance(results['gemini'], dict)
    assert isinstance(results['ollama'], dict)
    
    # Check ollama specifically
    assert 'ollama' in results['ollama']
    assert results['ollama']['ollama'] is True  # Should be installed


def test_verify_all_dependencies():
    """Test verifying all dependencies"""
    all_core_installed, missing_providers = DependencyChecker.verify_all_dependencies()
    
    # All core should be installed
    assert all_core_installed is True
    
    # Missing providers should be a list
    assert isinstance(missing_providers, list)
    
    # In our test environment, ollama should be installed
    assert 'ollama' not in missing_providers


def test_get_installation_help_message_for_provider():
    """Test getting installation help for specific provider"""
    help_msg = DependencyChecker.get_installation_help_message('ollama')
    
    assert isinstance(help_msg, str)
    assert 'ollama' in help_msg.lower()
    assert 'pip install' in help_msg.lower()
    assert 'requirements.txt' in help_msg


def test_get_installation_help_message_generic():
    """Test getting generic installation help"""
    help_msg = DependencyChecker.get_installation_help_message()
    
    assert isinstance(help_msg, str)
    assert 'pip install' in help_msg.lower()
    assert 'requirements.txt' in help_msg


def test_provider_dependencies_mapping():
    """Test that provider dependencies are correctly mapped"""
    deps = DependencyChecker.PROVIDER_DEPENDENCIES
    
    assert 'ollama' in deps
    assert 'ollama' in deps['ollama']
    
    assert 'openai' in deps
    assert 'openai' in deps['openai']
    
    assert 'claude' in deps
    assert 'anthropic' in deps['claude']
    
    assert 'gemini' in deps
    assert 'google.generativeai' in deps['gemini']


def test_core_dependencies_list():
    """Test that core dependencies list is not empty"""
    core_deps = DependencyChecker.CORE_DEPENDENCIES
    
    assert len(core_deps) > 0
    assert 'fastapi' in core_deps
    assert 'sqlalchemy' in core_deps
    assert 'uvicorn' in core_deps
    assert 'pydantic' in core_deps
