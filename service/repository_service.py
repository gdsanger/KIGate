"""
Repository service for managing GitHub repositories
"""
import httpx
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from model.repository import Repository, RepositoryCreate, RepositoryUpdate, RepositoryResponse
import config

logger = logging.getLogger(__name__)


class GitHubSyncError(Exception):
    """Custom exception for GitHub synchronization errors"""
    def __init__(self, message: str, error_type: str = "unknown"):
        super().__init__(message)
        self.error_type = error_type

class RepositoryService:
    """Service for managing GitHub repositories"""
    
    @staticmethod
    async def _determine_endpoint_type(client: httpx.AsyncClient, username_or_org: str) -> Optional[str]:
        """
        Determine if the given name is a user or organization
        
        Args:
            client: HTTP client to use for requests
            username_or_org: GitHub username or organization name
            
        Returns:
            "users" or "orgs" if found, None if neither exists
        """
        headers = {
            "Authorization": f"token {config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Try user endpoint first (most common case)
        try:
            user_url = f"{config.GITHUB_API_URL}/users/{username_or_org}"
            user_response = await client.get(user_url, headers=headers)
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                # Check if this is an organization account
                if user_data.get("type") == "Organization":
                    return "orgs"
                else:
                    return "users"
            elif user_response.status_code == 404:
                # User doesn't exist
                return None
            else:
                logger.warning(f"Unexpected response from GitHub user API: {user_response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error determining endpoint type for {username_or_org}: {str(e)}")
            return None
    
    @staticmethod
    async def fetch_repositories_from_github(username_or_org: str) -> List[Dict[str, Any]]:
        """
        Fetch repositories from GitHub API for a specific user or organization
        
        Args:
            username_or_org: GitHub username or organization name
            
        Returns:
            List of repository data from GitHub API
        """
        if not config.GITHUB_TOKEN:
            logger.warning(f"GitHub token not configured, cannot fetch repositories for {username_or_org}")
            return []
        
        if not username_or_org or not username_or_org.strip():
            logger.warning("Username or organization name is empty")
            return []
        
        username_or_org = username_or_org.strip()
        repositories = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First, determine if this is a user or organization
                endpoint_type = await RepositoryService._determine_endpoint_type(client, username_or_org)
                
                if not endpoint_type:
                    logger.warning(f"Could not find user or organization: {username_or_org}")
                    return []
                
                logger.info(f"Fetching repositories for {endpoint_type}: {username_or_org}")
                
                # Fetch all repositories with pagination
                page = 1
                per_page = 100
                
                while True:
                    url = f"{config.GITHUB_API_URL}/{endpoint_type}/{username_or_org}/repos"
                    headers = {
                        "Authorization": f"token {config.GITHUB_TOKEN}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                    params = {
                        "page": page,
                        "per_page": per_page,
                        "type": "all",  # public and private
                        "sort": "updated",
                        "direction": "desc"
                    }
                    
                    response = await client.get(url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        repos = response.json()
                        if not repos:  # No more repositories
                            break
                        
                        for repo in repos:
                            repositories.append({
                                "full_name": repo["full_name"],
                                "owner": repo["owner"]["login"],
                                "name": repo["name"],
                                "description": repo.get("description", ""),
                                "html_url": repo["html_url"],
                                "is_private": repo["private"]
                            })
                        
                        logger.info(f"Fetched {len(repos)} repositories from page {page}")
                        page += 1
                        
                        # GitHub API pagination limit (avoid infinite loops)
                        if page > 100:
                            logger.warning("Reached maximum pagination limit (100 pages)")
                            break
                            
                    elif response.status_code == 404:
                        logger.warning(f"No repositories found for {username_or_org} (404)")
                        break
                    elif response.status_code == 403:
                        logger.error(f"GitHub API rate limit exceeded or access denied for {username_or_org}")
                        break
                    else:
                        logger.error(f"GitHub API error {response.status_code}: {response.text}")
                        break
                        
        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching repositories for {username_or_org}")
        except Exception as e:
            logger.error(f"Error fetching repositories from GitHub for {username_or_org}: {str(e)}")
            
        logger.info(f"Successfully fetched {len(repositories)} repositories for {username_or_org}")
        return repositories
    
    @staticmethod
    async def sync_repositories(db: AsyncSession, username_or_org: str) -> int:
        """
        Sync repositories from GitHub API to database
        
        Args:
            db: Database session
            username_or_org: GitHub username or organization name
            
        Returns:
            Number of repositories synced
            
        Raises:
            GitHubSyncError: When sync fails for specific reasons
        """
        # Validate input
        if not username_or_org or not username_or_org.strip():
            raise GitHubSyncError("Benutzername oder Organisation ist erforderlich", "validation")
        
        username_or_org = username_or_org.strip()
        
        # Check if GitHub token is configured
        if not config.GITHUB_TOKEN:
            raise GitHubSyncError(
                "GitHub Token ist nicht konfiguriert. Bitte kontaktieren Sie den Administrator.", 
                "configuration"
            )
        
        try:
            # Fetch repositories from GitHub
            github_repos = await RepositoryService.fetch_repositories_from_github(username_or_org)
            
            if not github_repos:
                # Check if the user/org exists but has no repositories or doesn't exist
                async with httpx.AsyncClient(timeout=30.0) as client:
                    endpoint_type = await RepositoryService._determine_endpoint_type(client, username_or_org)
                    
                    if not endpoint_type:
                        raise GitHubSyncError(
                            f"Benutzer oder Organisation '{username_or_org}' wurde auf GitHub nicht gefunden. "
                            "Bitte überprüfen Sie die Schreibweise.",
                            "not_found"
                        )
                    else:
                        raise GitHubSyncError(
                            f"'{username_or_org}' wurde gefunden, hat aber keine öffentlichen oder zugänglichen Repositories. "
                            "Möglicherweise sind alle Repositories privat oder der GitHub Token hat keine Berechtigung.",
                            "no_repos"
                        )
            
            synced_count = 0
            
            for repo_data in github_repos:
                # Check if repository already exists
                existing_repo = await RepositoryService.get_repository_by_full_name(db, repo_data["full_name"])
                
                if existing_repo:
                    # Update existing repository
                    existing_repo.description = repo_data["description"]
                    existing_repo.html_url = repo_data["html_url"]
                    existing_repo.is_private = repo_data["is_private"]
                    existing_repo.last_updated = func.current_timestamp()
                else:
                    # Create new repository
                    new_repo = Repository(
                        full_name=repo_data["full_name"],
                        owner=repo_data["owner"],
                        name=repo_data["name"],
                        description=repo_data["description"],
                        html_url=repo_data["html_url"],
                        is_private=repo_data["is_private"],
                        is_active=True  # Default to active
                    )
                    db.add(new_repo)
                
                synced_count += 1
            
            await db.commit()
            logger.info(f"Synced {synced_count} repositories for {username_or_org}")
            return synced_count
            
        except GitHubSyncError:
            # Re-raise GitHub sync errors as-is
            await db.rollback()
            raise
        except httpx.TimeoutException:
            await db.rollback()
            raise GitHubSyncError(
                "Timeout beim Zugriff auf die GitHub API. Bitte versuchen Sie es später erneut.",
                "timeout"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error syncing repositories: {str(e)}")
            raise GitHubSyncError(
                f"Unerwarteter Fehler beim Synchronisieren: {str(e)}",
                "unexpected"
            )
    
    @staticmethod
    async def get_all_repositories(db: AsyncSession) -> List[Repository]:
        """
        Get all repositories from database
        
        Args:
            db: Database session
            
        Returns:
            List of Repository objects
        """
        result = await db.execute(
            select(Repository).order_by(Repository.full_name)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_active_repositories(db: AsyncSession) -> List[Repository]:
        """
        Get active repositories for dropdown
        
        Args:
            db: Database session
            
        Returns:
            List of active Repository objects
        """
        result = await db.execute(
            select(Repository)
            .where(Repository.is_active == True)
            .order_by(Repository.full_name)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_repository(db: AsyncSession, repo_id: int) -> Optional[Repository]:
        """
        Get repository by ID
        
        Args:
            db: Database session
            repo_id: Repository ID
            
        Returns:
            Repository object or None if not found
        """
        result = await db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_repository_by_full_name(db: AsyncSession, full_name: str) -> Optional[Repository]:
        """
        Get repository by full name (owner/repo)
        
        Args:
            db: Database session
            full_name: Repository full name
            
        Returns:
            Repository object or None if not found
        """
        result = await db.execute(
            select(Repository).where(Repository.full_name == full_name)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_repository(db: AsyncSession, repo_id: int, repo_data: RepositoryUpdate) -> Optional[Repository]:
        """
        Update repository
        
        Args:
            db: Database session
            repo_id: Repository ID
            repo_data: Update data
            
        Returns:
            Updated Repository object or None if not found
        """
        repo = await RepositoryService.get_repository(db, repo_id)
        if not repo:
            return None
        
        for field, value in repo_data.dict(exclude_unset=True).items():
            setattr(repo, field, value)
        
        repo.last_updated = func.current_timestamp()
        await db.commit()
        return repo
    
    @staticmethod
    async def toggle_repository_status(db: AsyncSession, repo_id: int) -> Optional[Repository]:
        """
        Toggle repository active status
        
        Args:
            db: Database session
            repo_id: Repository ID
            
        Returns:
            Updated Repository object or None if not found
        """
        repo = await RepositoryService.get_repository(db, repo_id)
        if not repo:
            return None
        
        repo.is_active = not repo.is_active
        repo.last_updated = func.current_timestamp()
        await db.commit()
        return repo
    
    @staticmethod
    async def delete_repository(db: AsyncSession, repo_id: int) -> bool:
        """
        Delete repository
        
        Args:
            db: Database session
            repo_id: Repository ID
            
        Returns:
            True if deleted, False if not found
        """
        repo = await RepositoryService.get_repository(db, repo_id)
        if not repo:
            return False
        
        await db.delete(repo)
        await db.commit()
        return True