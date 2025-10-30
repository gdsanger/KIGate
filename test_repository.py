"""
Tests for Repository functionality
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from model.user import Base
from model.repository import Repository
from service.repository_service import RepositoryService


@pytest_asyncio.fixture
async def test_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_crud(test_db):
    """Test basic CRUD operations for repositories"""
    # Create a test repository
    test_repo = Repository(
        full_name="test/repo",
        owner="test", 
        name="repo",
        description="Test repository",
        html_url="https://github.com/test/repo",
        is_private=False,
        is_active=True
    )
    
    test_db.add(test_repo)
    await test_db.commit()
    
    # Test get all repositories
    repos = await RepositoryService.get_all_repositories(test_db)
    assert len(repos) == 1
    assert repos[0].full_name == "test/repo"
    
    # Test get active repositories
    active_repos = await RepositoryService.get_active_repositories(test_db)
    assert len(active_repos) == 1
    assert active_repos[0].full_name == "test/repo"
    
    # Test get repository by full name
    found_repo = await RepositoryService.get_repository_by_full_name(test_db, "test/repo")
    assert found_repo is not None
    assert found_repo.full_name == "test/repo"
    
    # Test toggle repository status
    toggled_repo = await RepositoryService.toggle_repository_status(test_db, found_repo.id)
    assert toggled_repo is not None
    assert toggled_repo.is_active == False
    
    # Test that inactive repository is not in active list
    active_repos = await RepositoryService.get_active_repositories(test_db)
    assert len(active_repos) == 0


@pytest.mark.asyncio
async def test_fetch_repositories_without_token(test_db):
    """Test fetch repositories returns empty list without token"""
    repos = await RepositoryService.fetch_repositories_from_github("test-user")
    assert repos == []


if __name__ == "__main__":
    pytest.main([__file__])