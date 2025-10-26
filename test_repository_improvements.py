"""
Tests for the improved Repository functionality
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from service.repository_service import RepositoryService


@pytest.mark.asyncio
async def test_determine_endpoint_type_user():
    """Test endpoint type detection for a regular user"""
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "User", "login": "testuser"}
        mock_client.get.return_value = mock_response
        
        result = await RepositoryService._determine_endpoint_type(mock_client, "testuser")
        assert result == "users"


@pytest.mark.asyncio
async def test_determine_endpoint_type_organization():
    """Test endpoint type detection for an organization"""
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "Organization", "login": "testorg"}
        mock_client.get.return_value = mock_response
        
        result = await RepositoryService._determine_endpoint_type(mock_client, "testorg")
        assert result == "orgs"


@pytest.mark.asyncio
async def test_determine_endpoint_type_not_found():
    """Test endpoint type detection for non-existent user"""
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        
        result = await RepositoryService._determine_endpoint_type(mock_client, "nonexistent")
        assert result is None


@pytest.mark.asyncio
async def test_fetch_repositories_empty_username():
    """Test fetch repositories with empty username"""
    result = await RepositoryService.fetch_repositories_from_github("")
    assert result == []
    
    result = await RepositoryService.fetch_repositories_from_github("   ")
    assert result == []


@pytest.mark.asyncio
async def test_fetch_repositories_with_token_user_found():
    """Test successful repository fetching for a user"""
    mock_repos = [
        {
            "full_name": "testuser/repo1",
            "name": "repo1",
            "owner": {"login": "testuser"},
            "description": "Test repo 1",
            "html_url": "https://github.com/testuser/repo1",
            "private": False
        },
        {
            "full_name": "testuser/repo2",
            "name": "repo2",
            "owner": {"login": "testuser"},
            "description": "Test repo 2",
            "html_url": "https://github.com/testuser/repo2",
            "private": True
        }
    ]
    
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'), \
         patch('service.repository_service.RepositoryService._determine_endpoint_type', return_value="users"), \
         patch('httpx.AsyncClient') as mock_client_class:
        
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock first request returns repos, second returns empty (pagination end)
        mock_responses = [
            MagicMock(status_code=200, json=lambda: mock_repos),
            MagicMock(status_code=200, json=lambda: [])
        ]
        mock_client.get.side_effect = mock_responses
        
        result = await RepositoryService.fetch_repositories_from_github("testuser")
        
        assert len(result) == 2
        assert result[0]["full_name"] == "testuser/repo1"
        assert result[0]["is_private"] == False
        assert result[1]["full_name"] == "testuser/repo2"
        assert result[1]["is_private"] == True


@pytest.mark.asyncio
async def test_fetch_repositories_user_not_found():
    """Test repository fetching when user is not found"""
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'), \
         patch('service.repository_service.RepositoryService._determine_endpoint_type', return_value=None):
        
        result = await RepositoryService.fetch_repositories_from_github("nonexistent")
        assert result == []


@pytest.mark.asyncio
async def test_fetch_repositories_api_error():
    """Test repository fetching with API error"""
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'), \
         patch('service.repository_service.RepositoryService._determine_endpoint_type', return_value="users"), \
         patch('httpx.AsyncClient') as mock_client_class:
        
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock API error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_client.get.return_value = mock_response
        
        result = await RepositoryService.fetch_repositories_from_github("testuser")
        assert result == []


@pytest.mark.asyncio
async def test_fetch_repositories_rate_limit():
    """Test repository fetching with rate limit error"""
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'), \
         patch('service.repository_service.RepositoryService._determine_endpoint_type', return_value="users"), \
         patch('httpx.AsyncClient') as mock_client_class:
        
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock rate limit response
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Rate limit exceeded"
        mock_client.get.return_value = mock_response
        
        result = await RepositoryService.fetch_repositories_from_github("testuser")
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__])