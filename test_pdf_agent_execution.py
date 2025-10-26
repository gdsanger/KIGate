"""
Test cases for PDF Agent Execution functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import UploadFile
import io
from service.pdf_service import PDFService
from model.pdf_agent_execution import PDFAgentExecutionRequest, PDFAgentExecutionResponse


class TestPDFService:
    """Test cases for PDF service functionality"""
    
    def test_chunk_text_small_text(self):
        """Test that small text is not chunked"""
        text = "This is a small text that should not be chunked."
        chunks = PDFService.chunk_text(text, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_large_text(self):
        """Test that large text is properly chunked"""
        # Create a text larger than chunk_size
        text = "This is a sentence. " * 300  # About 6000 characters
        chunks = PDFService.chunk_text(text, chunk_size=1000)
        
        assert len(chunks) > 1
        # Check that no chunk exceeds the limit significantly
        for chunk in chunks:
            assert len(chunk) <= 1200  # Allow some flexibility for sentence boundaries
    
    def test_chunk_text_sentence_boundaries(self):
        """Test that chunking respects sentence boundaries"""
        text = "First sentence. Second sentence. " * 50 + "Final sentence."
        chunks = PDFService.chunk_text(text, chunk_size=500)
        
        # Most chunks should end with proper punctuation
        for chunk in chunks[:-1]:  # All chunks except the last
            assert chunk.strip()[-1] in '.!?'
    
    def test_merge_chunk_results_single(self):
        """Test merging single result"""
        results = ["Single result"]
        merged = PDFService.merge_chunk_results(results, "test-agent")
        assert merged == "Single result"
    
    def test_merge_chunk_results_multiple(self):
        """Test merging multiple results"""
        results = ["Result 1", "Result 2", "Result 3"]
        merged = PDFService.merge_chunk_results(results, "test-agent")
        
        assert "test-agent Analysis Results" in merged
        assert "Section 1 Results" in merged
        assert "Section 2 Results" in merged
        assert "Section 3 Results" in merged
        assert "Total sections processed: 3" in merged
    
    def test_merge_chunk_results_empty(self):
        """Test merging empty results"""
        results = []
        merged = PDFService.merge_chunk_results(results, "test-agent")
        assert merged == "No results to merge."
    
    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_invalid_file(self):
        """Test PDF text extraction with invalid file"""
        # Create a mock UploadFile with invalid content
        invalid_content = b"This is not a PDF file"
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=invalid_content)
        mock_file.filename = "test.pdf"
        
        with pytest.raises(Exception):  # Should raise HTTPException or similar
            await PDFService.extract_text_from_pdf(mock_file)


class TestPDFAgentExecutionModels:
    """Test cases for PDF agent execution models"""
    
    def test_pdf_agent_execution_request_validation(self):
        """Test PDF agent execution request model validation"""
        # Valid request
        request_data = {
            "agent_name": "test-agent",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": "test-user-123",
            "chunk_size": 4000
        }
        request = PDFAgentExecutionRequest(**request_data)
        assert request.agent_name == "test-agent"
        assert request.chunk_size == 4000
    
    def test_pdf_agent_execution_request_default_chunk_size(self):
        """Test PDF agent execution request with default chunk size"""
        request_data = {
            "agent_name": "test-agent",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": "test-user-123"
        }
        request = PDFAgentExecutionRequest(**request_data)
        assert request.chunk_size == 4000  # Default value
    
    def test_pdf_agent_execution_response_creation(self):
        """Test PDF agent execution response model creation"""
        response_data = {
            "job_id": "job-123",
            "agent": "test-agent",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "status": "completed",
            "result": "Analysis complete",
            "chunks_processed": 3,
            "pdf_filename": "test.pdf"
        }
        response = PDFAgentExecutionResponse(**response_data)
        assert response.job_id == "job-123"
        assert response.chunks_processed == 3
        assert response.pdf_filename == "test.pdf"


if __name__ == "__main__":
    pytest.main([__file__])