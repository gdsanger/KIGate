"""
Tests for the improved sync functionality
"""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from model.user import Base
from service.repository_service import RepositoryService, GitHubSyncError


@pytest_asyncio.fixture
async def test_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_repositories_empty_username(test_db):
    """Test sync with empty username"""
    with pytest.raises(GitHubSyncError) as exc_info:
        await RepositoryService.sync_repositories(test_db, "")
    assert exc_info.value.error_type == "validation"
    assert "erforderlich" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_repositories_no_token(test_db):
    """Test sync without GitHub token"""
    with patch('service.repository_service.config.GITHUB_TOKEN', ''):
        with pytest.raises(GitHubSyncError) as exc_info:
            await RepositoryService.sync_repositories(test_db, "testuser")
        assert exc_info.value.error_type == "configuration"
        assert "nicht konfiguriert" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_repositories_user_not_found(test_db):
    """Test sync with non-existent user"""
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'), \
         patch('service.repository_service.RepositoryService.fetch_repositories_from_github', return_value=[]), \
         patch('service.repository_service.RepositoryService._determine_endpoint_type', return_value=None):
        
        with pytest.raises(GitHubSyncError) as exc_info:
            await RepositoryService.sync_repositories(test_db, "nonexistent")
        assert exc_info.value.error_type == "not_found"
        assert "nicht gefunden" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_repositories_no_accessible_repos(test_db):
    """Test sync when user exists but has no accessible repos"""
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'), \
         patch('service.repository_service.RepositoryService.fetch_repositories_from_github', return_value=[]), \
         patch('service.repository_service.RepositoryService._determine_endpoint_type', return_value="users"):
        
        with pytest.raises(GitHubSyncError) as exc_info:
            await RepositoryService.sync_repositories(test_db, "testuser")
        assert exc_info.value.error_type == "no_repos"
        assert "keine öffentlichen" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_repositories_success(test_db):
    """Test successful repository sync"""
    mock_repos = [
        {
            "full_name": "testuser/repo1",
            "owner": "testuser",
            "name": "repo1",
            "description": "Test repo 1",
            "html_url": "https://github.com/testuser/repo1",
            "is_private": False
        }
    ]
    
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'), \
         patch('service.repository_service.RepositoryService.fetch_repositories_from_github', return_value=mock_repos):
        
        result = await RepositoryService.sync_repositories(test_db, "testuser")
        assert result == 1


@pytest.mark.asyncio
async def test_sync_repositories_update_existing(test_db):
    """Test sync updates existing repositories"""
    from model.repository import Repository
    
    # Add existing repository
    existing_repo = Repository(
        full_name="testuser/repo1",
        owner="testuser", 
        name="repo1",
        description="Old description",
        html_url="https://github.com/testuser/repo1",
        is_private=False,
        is_active=True
    )
    test_db.add(existing_repo)
    await test_db.commit()
    
    mock_repos = [
        {
            "full_name": "testuser/repo1",
            "owner": "testuser",
            "name": "repo1",
            "description": "Updated description",
            "html_url": "https://github.com/testuser/repo1",
            "is_private": True  # Changed to private
        }
    ]
    
    with patch('service.repository_service.config.GITHUB_TOKEN', 'test_token'), \
         patch('service.repository_service.RepositoryService.fetch_repositories_from_github', return_value=mock_repos):
        
        result = await RepositoryService.sync_repositories(test_db, "testuser")
        assert result == 1
        
        # Check that the repository was updated
        updated_repo = await RepositoryService.get_repository_by_full_name(test_db, "testuser/repo1")
        assert updated_repo.description == "Updated description"
        assert updated_repo.is_private == True


if __name__ == "__main__":
    pytest.main([__file__])