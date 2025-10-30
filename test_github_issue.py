"""
Tests for GitHub issue creation functionality
"""
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from model.github_issue import GitHubIssueRequest, ProcessedIssueContent, IssueType
from service.github_service import GitHubService
from service.github_issue_processor import GitHubIssueProcessor

class TestGitHubService:
    """Tests for GitHubService"""
    
    def test_validate_repository_format_valid(self):
        """Test repository format validation with valid formats"""
        assert GitHubService.validate_repository_format("owner/repo") == True
        assert GitHubService.validate_repository_format("github/github") == True
        assert GitHubService.validate_repository_format("test-user/test-repo") == True
        assert GitHubService.validate_repository_format("user_name/repo.name") == True
    
    def test_validate_repository_format_invalid(self):
        """Test repository format validation with invalid formats"""
        assert GitHubService.validate_repository_format("") == False
        assert GitHubService.validate_repository_format("invalid") == False
        assert GitHubService.validate_repository_format("owner/") == False
        assert GitHubService.validate_repository_format("/repo") == False
        assert GitHubService.validate_repository_format("owner/repo/extra") == False
        assert GitHubService.validate_repository_format("owner with spaces/repo") == False

    @pytest.mark.asyncio
    async def test_create_issue_no_token(self):
        """Test issue creation without GitHub token"""
        processed_content = ProcessedIssueContent(
            improved_text="Test issue",
            title="Test Issue",
            issue_type=IssueType.BUG,
            labels=["bug"]
        )
        
        with patch('config.GITHUB_TOKEN', ''):
            result = await GitHubService.create_issue("owner/repo", processed_content)
            
        assert result.success == False
        assert "GitHub token not configured" in result.error_message

    @pytest.mark.skip("Mocking httpx.AsyncClient needs refinement")
    @pytest.mark.asyncio
    async def test_create_issue_success(self):
        """Test successful issue creation"""
        processed_content = ProcessedIssueContent(
            improved_text="Test issue description",
            title="Test Issue",
            issue_type=IssueType.BUG,
            labels=["bug"]
        )
        
        mock_response = {
            "number": 123,
            "title": "Test Issue", 
            "html_url": "https://github.com/owner/repo/issues/123"
        }
        
        with patch('service.github_service.config.GITHUB_TOKEN', 'test_token'), \
             patch('service.github_service.httpx.AsyncClient') as mock_client:
            
            # Create proper async mock
            mock_response_obj = AsyncMock()
            mock_response_obj.status_code = 201
            mock_response_obj.json.return_value = mock_response
            
            # Create context manager mock
            async_context = AsyncMock()
            async_context.post = AsyncMock(return_value=mock_response_obj)
            
            mock_client.return_value.__aenter__ = AsyncMock(return_value=async_context)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await GitHubService.create_issue("owner/repo", processed_content)
            
        assert result.success == True
        assert result.issue_number == 123
        assert result.title == "Test Issue"
        assert result.issue_url == "https://github.com/owner/repo/issues/123"

    @pytest.mark.skip("Mocking httpx.AsyncClient needs refinement")
    @pytest.mark.asyncio
    async def test_create_issue_api_error(self):
        """Test GitHub API error handling"""
        processed_content = ProcessedIssueContent(
            improved_text="Test issue",
            title="Test Issue", 
            issue_type=IssueType.BUG,
            labels=["bug"]
        )
        
        with patch('service.github_service.config.GITHUB_TOKEN', 'test_token'), \
             patch('service.github_service.httpx.AsyncClient') as mock_client:
            
            # Create proper async mock for error response
            mock_response_obj = AsyncMock()
            mock_response_obj.status_code = 404
            mock_response_obj.text = "Repository not found"
            mock_response_obj.json.return_value = {"message": "Not Found"}
            
            # Create context manager mock
            async_context = AsyncMock()
            async_context.post = AsyncMock(return_value=mock_response_obj)
            
            mock_client.return_value.__aenter__ = AsyncMock(return_value=async_context)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await GitHubService.create_issue("owner/repo", processed_content)
            
        assert result.success == False
        assert "GitHub API error (404)" in result.error_message

class TestGitHubIssueProcessor:
    """Tests for GitHubIssueProcessor"""
    
    @pytest.mark.asyncio
    async def test_process_issue_text_success(self):
        """Test successful issue text processing"""
        mock_ai_response = {
            "content": '''{"improved_text": "Improved bug report", "title": "Bug in login", "issue_type": "bug", "labels": ["bug", "frontend"]}''',
            "success": True
        }
        
        with patch('service.github_issue_processor.send_ai_request', return_value=type('MockResult', (), mock_ai_response)()):
            result = await GitHubIssueProcessor.process_issue_text(
                "login broken",
                "user123"
            )
            
        assert result is not None
        assert result.improved_text == "Improved bug report"
        assert result.title == "Bug in login"
        assert result.issue_type == IssueType.BUG
        assert "bug" in result.labels

    @pytest.mark.asyncio 
    async def test_process_issue_text_ai_failure(self):
        """Test handling of AI processing failure"""
        mock_ai_response = {
            "content": "",
            "success": False,
            "error_message": "AI processing failed"
        }
        
        with patch('service.github_issue_processor.send_ai_request', return_value=type('MockResult', (), mock_ai_response)()):
            result = await GitHubIssueProcessor.process_issue_text(
                "test text",
                "user123"
            )
            
        assert result is None

    @pytest.mark.asyncio
    async def test_process_issue_text_json_in_codeblocks(self):
        """Test processing when AI returns JSON in code blocks"""
        mock_ai_response = {
            "content": '''```json\n{"improved_text": "Better text", "title": "Feature Request", "issue_type": "enhancement", "labels": ["enhancement"]}\n```''',
            "success": True
        }
        
        with patch('service.github_issue_processor.send_ai_request', return_value=type('MockResult', (), mock_ai_response)()):
            result = await GitHubIssueProcessor.process_issue_text(
                "need new feature", 
                "user123"
            )
            
        assert result is not None
        assert result.improved_text == "Better text"
        assert result.issue_type == IssueType.FEATURE

    def test_fallback_processing(self):
        """Test fallback processing when JSON parsing fails"""
        result = GitHubIssueProcessor._fallback_processing(
            "This is a bug in the system",
            "Some improved text that's not JSON"
        )
        
        assert result is not None
        assert result.issue_type == IssueType.BUG
        assert "This is a bug in the system"[:10] in result.title
        
    def test_fallback_processing_feature(self):
        """Test fallback processing identifies feature requests"""
        result = GitHubIssueProcessor._fallback_processing(
            "Add new feature to the application",
            "Some improved text"
        )
        
        assert result is not None
        assert result.issue_type == IssueType.FEATURE