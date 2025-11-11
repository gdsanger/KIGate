"""
Test output token logging functionality across all AI controllers
"""
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult
from controller.api_openai import OpenAIController
from controller.api_claude import ClaudeController
from controller.api_gemini import GeminiController
from controller.api_ollama import OllamaController
from service.job_service import JobService
from model.job import Job
from sqlalchemy.ext.asyncio import AsyncSession

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_openai_token_extraction():
    """Test that OpenAI controller extracts input and output tokens correctly"""
    print("\nTesting OpenAI token extraction...")
    
    with patch('controller.api_openai.AsyncOpenAI') as mock_client_class:
        # Set up mock response with token usage
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 150
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        
        # Set up mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Create controller with fake key
        controller = OpenAIController(strict_mode=False, api_key="fake-test-key")
        
        # Create test request
        request = aiapirequest(
            job_id="test-job-1",
            user_id="test-user-1",
            model="gpt-3.5-turbo",
            message="Test message"
        )
        
        # Process request
        result = await controller.process_request(request)
        
        # Verify token extraction
        assert result.success, "Request should succeed"
        assert result.tokens_used == 150, f"Expected 150 total tokens, got {result.tokens_used}"
        assert result.input_tokens == 100, f"Expected 100 input tokens, got {result.input_tokens}"
        assert result.output_tokens == 50, f"Expected 50 output tokens, got {result.output_tokens}"
        
        print(f"✓ OpenAI correctly extracted tokens: total={result.tokens_used}, input={result.input_tokens}, output={result.output_tokens}")


async def test_claude_token_extraction():
    """Test that Claude controller extracts input and output tokens correctly"""
    print("\nTesting Claude token extraction...")
    
    with patch('controller.api_claude.AsyncAnthropic') as mock_client_class:
        # Set up mock response with token usage
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 80
        mock_response.usage.output_tokens = 40
        
        # Set up mock client
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Create controller with fake key
        controller = ClaudeController(strict_mode=False, api_key="fake-test-key")
        
        # Create test request
        request = aiapirequest(
            job_id="test-job-2",
            user_id="test-user-2",
            model="claude-3-opus-20240229",
            message="Test message"
        )
        
        # Process request
        result = await controller.process_request(request)
        
        # Verify token extraction
        assert result.success, "Request should succeed"
        assert result.tokens_used == 120, f"Expected 120 total tokens, got {result.tokens_used}"
        assert result.input_tokens == 80, f"Expected 80 input tokens, got {result.input_tokens}"
        assert result.output_tokens == 40, f"Expected 40 output tokens, got {result.output_tokens}"
        
        print(f"✓ Claude correctly extracted tokens: total={result.tokens_used}, input={result.input_tokens}, output={result.output_tokens}")


async def test_gemini_token_extraction():
    """Test that Gemini controller extracts input and output tokens correctly"""
    print("\nTesting Gemini token extraction...")
    
    with patch('controller.api_gemini.genai') as mock_genai:
        # Set up mock response with token usage
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.total_token_count = 200
        mock_response.usage_metadata.prompt_token_count = 120
        mock_response.usage_metadata.candidates_token_count = 80
        
        # Set up mock model
        mock_model = MagicMock()
        mock_model.generate_content = MagicMock(return_value=mock_response)
        
        # Mock the GenerativeModel class
        mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
        mock_genai.configure = MagicMock()
        
        # Create controller with fake key
        controller = GeminiController(strict_mode=False, api_key="fake-test-key")
        
        # Create test request
        request = aiapirequest(
            job_id="test-job-3",
            user_id="test-user-3",
            model="gemini-pro",
            message="Test message"
        )
        
        # Process request
        result = await controller.process_request(request)
        
        # Verify token extraction
        assert result.success, "Request should succeed"
        assert result.tokens_used == 200, f"Expected 200 total tokens, got {result.tokens_used}"
        assert result.input_tokens == 120, f"Expected 120 input tokens, got {result.input_tokens}"
        assert result.output_tokens == 80, f"Expected 80 output tokens, got {result.output_tokens}"
        
        print(f"✓ Gemini correctly extracted tokens: total={result.tokens_used}, input={result.input_tokens}, output={result.output_tokens}")


async def test_ollama_token_defaults():
    """Test that Ollama controller returns zero tokens (as expected)"""
    print("\nTesting Ollama token defaults...")
    
    with patch('controller.api_ollama.AsyncClient') as mock_client_class:
        # Set up mock response (no token usage)
        mock_response = MagicMock()
        mock_response.message = MagicMock()
        mock_response.message.content = "Test response"
        
        # Set up mock client
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Create controller with fake URL
        controller = OllamaController(strict_mode=False, api_url="http://localhost:11434")
        
        # Create test request
        request = aiapirequest(
            job_id="test-job-4",
            user_id="test-user-4",
            model="llama2",
            message="Test message"
        )
        
        # Process request
        result = await controller.process_request(request)
        
        # Verify token defaults (Ollama doesn't provide tokens)
        assert result.success, "Request should succeed"
        assert result.tokens_used == 0, f"Expected 0 total tokens, got {result.tokens_used}"
        assert result.input_tokens == 0, f"Expected 0 input tokens, got {result.input_tokens}"
        assert result.output_tokens == 0, f"Expected 0 output tokens, got {result.output_tokens}"
        
        print(f"✓ Ollama correctly defaults to zero tokens: total={result.tokens_used}, input={result.input_tokens}, output={result.output_tokens}")


async def test_aiapiresult_model():
    """Test that aiapiresult model has the required token fields"""
    print("\nTesting aiapiresult model...")
    
    # Create aiapiresult with all fields
    result = aiapiresult(
        job_id="test-job",
        user_id="test-user",
        content="Test content",
        success=True,
        error_message=None,
        tokens_used=100,
        input_tokens=60,
        output_tokens=40
    )
    
    # Verify all fields
    assert result.tokens_used == 100, "tokens_used field should be set"
    assert result.input_tokens == 60, "input_tokens field should be set"
    assert result.output_tokens == 40, "output_tokens field should be set"
    
    # Test with default values
    result_defaults = aiapiresult(
        job_id="test-job-2",
        user_id="test-user-2",
        content="Test",
        success=True
    )
    
    assert result_defaults.tokens_used == 0, "tokens_used should default to 0"
    assert result_defaults.input_tokens == 0, "input_tokens should default to 0"
    assert result_defaults.output_tokens == 0, "output_tokens should default to 0"
    
    print("✓ aiapiresult model has correct token fields with proper defaults")


async def test_job_service_token_updates():
    """Test that JobService can update input and output token counts"""
    print("\nTesting JobService token update methods...")
    
    # Create a mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Create a mock job
    mock_job = Job(
        id="test-job-id",
        name="test-job",
        user_id="test-user",
        provider="openai",
        model="gpt-3.5-turbo",
        status="created"
    )
    
    # Mock the database query results
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_job
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    
    # Test update_job_token_count
    success = await JobService.update_job_token_count(mock_db, "test-job-id", 100)
    assert success, "update_job_token_count should return True"
    assert mock_job.token_count == 100, "token_count should be updated"
    
    # Test update_job_output_token_count
    success = await JobService.update_job_output_token_count(mock_db, "test-job-id", 50)
    assert success, "update_job_output_token_count should return True"
    assert mock_job.output_token_count == 50, "output_token_count should be updated"
    
    print(f"✓ JobService correctly updates token counts: input={mock_job.token_count}, output={mock_job.output_token_count}")


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running Output Token Logging Tests")
    print("=" * 60)
    
    try:
        await test_aiapiresult_model()
        await test_openai_token_extraction()
        await test_claude_token_extraction()
        await test_gemini_token_extraction()
        await test_ollama_token_defaults()
        await test_job_service_token_updates()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
