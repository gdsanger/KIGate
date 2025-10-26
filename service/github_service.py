"""
GitHub Service for creating issues via GitHub API
"""
import httpx
from typing import Optional
from model.github_issue import GitHubIssueResponse, ProcessedIssueContent, IssueType
import config

class GitHubService:
    """Service for interacting with GitHub API"""
    
    @staticmethod
    async def create_issue(repository: str, processed_content: ProcessedIssueContent) -> GitHubIssueResponse:
        """
        Create a GitHub issue using the GitHub API
        
        Args:
            repository: Repository in format "owner/repo"
            processed_content: AI-processed issue content
            
        Returns:
            GitHubIssueResponse with issue details or error
        """
        if not config.GITHUB_TOKEN:
            return GitHubIssueResponse(
                issue_number=0,
                title="",
                issue_url="",
                success=False,
                error_message="GitHub token not configured"
            )
        
        try:
            # Prepare issue data
            issue_data = {
                "title": processed_content.title,
                "body": processed_content.improved_text,
                "labels": processed_content.labels
            }
            
            # Add issue type as label if not already present
            if processed_content.issue_type.value not in processed_content.labels:
                issue_data["labels"].append(processed_content.issue_type.value)
            
            # Make API request
            url = f"{config.GITHUB_API_URL}/repos/{repository}/issues"
            headers = {
                "Authorization": f"token {config.GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=issue_data, headers=headers)
                
                if response.status_code == 201:
                    # Issue created successfully
                    issue_data = response.json()
                    return GitHubIssueResponse(
                        issue_number=issue_data["number"],
                        title=issue_data["title"],
                        issue_url=issue_data["html_url"],
                        success=True
                    )
                else:
                    # Handle error
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("message", error_detail)
                    except (ValueError, KeyError):
                        pass
                    
                    return GitHubIssueResponse(
                        issue_number=0,
                        title="",
                        issue_url="",
                        success=False,
                        error_message=f"GitHub API error ({response.status_code}): {error_detail}"
                    )
                    
        except httpx.RequestError as e:
            return GitHubIssueResponse(
                issue_number=0,
                title="",
                issue_url="",
                success=False,
                error_message=f"Network error: {str(e)}"
            )
        except Exception as e:
            return GitHubIssueResponse(
                issue_number=0,
                title="",
                issue_url="",
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    @staticmethod
    def validate_repository_format(repository: str) -> bool:
        """
        Validate repository format (owner/repo)
        
        Args:
            repository: Repository string to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not repository or "/" not in repository:
            return False
        
        parts = repository.split("/")
        if len(parts) != 2:
            return False
        
        owner, repo = parts
        if not owner or not repo:
            return False
        
        # Basic validation for GitHub username/org and repo name
        if not owner.replace("-", "").replace("_", "").replace(".", "").isalnum():
            return False
        if not repo.replace("-", "").replace("_", "").replace(".", "").isalnum():
            return False
            
        return True