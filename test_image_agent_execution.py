"""
Test cases for Image Agent Execution functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import UploadFile, HTTPException
import io
import base64
from service.image_service import ImageService
from model.image_agent_execution import ImageAgentExecutionRequest, ImageAgentExecutionResponse


class TestImageService:
    """Test cases for Image service functionality"""
    
    def test_validate_image_type_png(self):
        """Test validation of PNG image type"""
        assert ImageService.validate_image_type("image/png", "test.png") == True
    
    def test_validate_image_type_jpeg(self):
        """Test validation of JPEG image type"""
        assert ImageService.validate_image_type("image/jpeg", "test.jpg") == True
        assert ImageService.validate_image_type("image/jpeg", "test.jpeg") == True
    
    def test_validate_image_type_webp(self):
        """Test validation of WEBP image type"""
        assert ImageService.validate_image_type("image/webp", "test.webp") == True
    
    def test_validate_image_type_fallback_extension(self):
        """Test validation with missing MIME type but valid extension"""
        assert ImageService.validate_image_type(None, "test.png") == True
        assert ImageService.validate_image_type("", "test.jpg") == True
    
    def test_validate_image_type_invalid(self):
        """Test validation of invalid image type"""
        with pytest.raises(HTTPException) as exc_info:
            ImageService.validate_image_type("application/pdf", "test.pdf")
        assert exc_info.value.status_code == 400
        assert "Unsupported image format" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_convert_image_to_base64_success(self):
        """Test successful image to base64 conversion"""
        # Create a small test image content (1x1 PNG)
        # This is a minimal valid PNG file
        png_content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=png_content)
        mock_file.filename = "test.png"
        
        result = await ImageService.convert_image_to_base64(mock_file)
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Verify it's valid base64
        base64.b64decode(result)
    
    @pytest.mark.asyncio
    async def test_convert_image_to_base64_too_large(self):
        """Test image size validation"""
        # Create content larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)
        
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=large_content)
        mock_file.filename = "large.png"
        
        with pytest.raises(HTTPException) as exc_info:
            await ImageService.convert_image_to_base64(mock_file)
        
        assert exc_info.value.status_code == 400
        assert "too large" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_convert_image_to_base64_empty(self):
        """Test handling of empty image file"""
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=b"")
        mock_file.filename = "empty.png"
        
        result = await ImageService.convert_image_to_base64(mock_file)
        
        # Empty file should still convert to base64 (empty string)
        assert result == ""


class TestImageAgentExecutionModels:
    """Test cases for Image agent execution models"""
    
    def test_image_agent_execution_request_validation(self):
        """Test Image agent execution request model validation"""
        # Valid request with all fields
        request_data = {
            "agent_name": "image-ocr-extractor-de",
            "provider": "Ollama",
            "model": "qwen3-vl:8b",
            "user_id": "test-user-123",
            "parameters": {"key": "value"}
        }
        request = ImageAgentExecutionRequest(**request_data)
        assert request.agent_name == "image-ocr-extractor-de"
        assert request.provider == "Ollama"
        assert request.model == "qwen3-vl:8b"
        assert request.user_id == "test-user-123"
        assert request.parameters == {"key": "value"}
    
    def test_image_agent_execution_request_minimal(self):
        """Test Image agent execution request with minimal required fields"""
        # Minimal request
        request_data = {
            "agent_name": "image-ocr-extractor-de",
            "user_id": "test-user-123"
        }
        request = ImageAgentExecutionRequest(**request_data)
        assert request.agent_name == "image-ocr-extractor-de"
        assert request.user_id == "test-user-123"
        assert request.provider is None
        assert request.model is None
        assert request.parameters is None
    
    def test_image_agent_execution_request_invalid_agent_name(self):
        """Test validation with invalid agent name"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ImageAgentExecutionRequest(
                agent_name="",  # Empty string should fail
                user_id="test-user-123"
            )
    
    def test_image_agent_execution_request_invalid_user_id(self):
        """Test validation with invalid user ID"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ImageAgentExecutionRequest(
                agent_name="test-agent",
                user_id=""  # Empty string should fail
            )
    
    def test_image_agent_execution_response_success(self):
        """Test Image agent execution response model for success case"""
        response_data = {
            "success": True,
            "text": "Extracted text from invoice",
            "agent": "image-ocr-extractor-de",
            "provider": "Ollama",
            "model": "qwen3-vl:8b",
            "job_id": "job-123",
            "image_filename": "invoice.png"
        }
        response = ImageAgentExecutionResponse(**response_data)
        assert response.success == True
        assert response.text == "Extracted text from invoice"
        assert response.agent == "image-ocr-extractor-de"
        assert response.job_id == "job-123"
    
    def test_image_agent_execution_response_failure(self):
        """Test Image agent execution response model for failure case"""
        response_data = {
            "success": False,
            "text": "Error: Failed to process image",
            "agent": "image-ocr-extractor-de",
            "provider": "Ollama",
            "model": "qwen3-vl:8b",
            "job_id": "job-456",
            "image_filename": "receipt.jpg"
        }
        response = ImageAgentExecutionResponse(**response_data)
        assert response.success == False
        assert "Error" in response.text
        assert response.job_id == "job-456"


class TestOllamaVisionIntegration:
    """Test cases for Ollama vision controller integration"""
    
    @pytest.mark.asyncio
    async def test_process_vision_request_structure(self):
        """Test that vision request is properly structured"""
        from controller.api_ollama import OllamaController
        from model.aiapirequest import aiapirequest
        
        # Mock the AsyncClient
        with patch('controller.api_ollama.AsyncClient') as MockClient:
            mock_client = MockClient.return_value
            mock_response = Mock()
            mock_response.message = Mock()
            mock_response.message.content = "Extracted text: Invoice #123"
            mock_client.chat = AsyncMock(return_value=mock_response)
            
            controller = OllamaController(strict_mode=False, api_url="http://localhost:11434")
            controller.client = mock_client
            
            request = aiapirequest(
                job_id="test-job",
                user_id="test-user",
                model="qwen3-vl:8b",
                message="Extract text from this image"
            )
            
            image_base64 = "base64encodedimagedata"
            
            result = await controller.process_vision_request(request, image_base64)
            
            # Verify the result
            assert result.success == True
            assert result.content == "Extracted text: Invoice #123"
            assert result.job_id == "test-job"
            
            # Verify that chat was called with correct parameters
            mock_client.chat.assert_called_once()
            call_args = mock_client.chat.call_args
            
            # Check that messages contain the image
            messages = call_args.kwargs['messages']
            assert len(messages) == 1
            assert messages[0]['role'] == 'user'
            assert messages[0]['content'] == "Extract text from this image"
            assert 'images' in messages[0]
            assert messages[0]['images'][0] == image_base64
