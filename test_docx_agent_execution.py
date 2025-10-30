"""
Test cases for DOCX Agent Execution functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import UploadFile
import io
from service.docx_service import DocxService
from model.docx_agent_execution import DocxAgentExecutionRequest, DocxAgentExecutionResponse


class TestDocxService:
    """Test cases for DOCX service functionality"""
    
    def test_chunk_text_small_text(self):
        """Test that small text is not chunked"""
        text = "This is a small text that should not be chunked."
        chunks = DocxService.chunk_text(text, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_large_text(self):
        """Test that large text is properly chunked"""
        # Create a text larger than chunk_size
        text = "This is a sentence. " * 300  # About 6000 characters
        chunks = DocxService.chunk_text(text, chunk_size=1000)
        
        assert len(chunks) > 1
        # Check that no chunk exceeds the limit significantly
        for chunk in chunks:
            assert len(chunk) <= 1200  # Allow some flexibility for sentence boundaries
    
    def test_chunk_text_sentence_boundaries(self):
        """Test that chunking respects sentence boundaries"""
        text = "First sentence. Second sentence. " * 50 + "Final sentence."
        chunks = DocxService.chunk_text(text, chunk_size=500)
        
        # Most chunks should end with proper punctuation
        for chunk in chunks[:-1]:  # All chunks except the last
            assert chunk.strip()[-1] in '.!?'
    
    def test_merge_chunk_results_single(self):
        """Test merging single result"""
        results = ["Single result"]
        merged = DocxService.merge_chunk_results(results, "test-agent")
        assert merged == "Single result"
    
    def test_merge_chunk_results_multiple(self):
        """Test merging multiple results"""
        results = ["Result 1", "Result 2", "Result 3"]
        merged = DocxService.merge_chunk_results(results, "test-agent")
        
        assert "test-agent Analysis Results" in merged
        assert "Section 1 Results" in merged
        assert "Section 2 Results" in merged
        assert "Section 3 Results" in merged
        assert "Total sections processed: 3" in merged
    
    def test_merge_chunk_results_empty(self):
        """Test merging empty results"""
        results = []
        merged = DocxService.merge_chunk_results(results, "test-agent")
        assert merged == "No results to merge."
    
    @pytest.mark.asyncio
    async def test_extract_text_from_docx_invalid_file(self):
        """Test DOCX text extraction with invalid file"""
        # Create a mock UploadFile with invalid content
        invalid_content = b"This is not a DOCX file"
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=invalid_content)
        mock_file.filename = "test.docx"
        
        with pytest.raises(Exception):  # Should raise HTTPException or similar
            await DocxService.extract_text_from_docx(mock_file)
    
    @pytest.mark.asyncio
    async def test_extract_text_from_docx_empty_file(self):
        """Test DOCX text extraction with empty file"""
        # Mock an empty DOCX document
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "empty.docx"
        
        # Mock the docx.Document to return empty paragraphs and tables
        with patch('service.docx_service.Document') as mock_document:
            mock_doc = Mock()
            mock_doc.paragraphs = []  # No paragraphs
            mock_doc.tables = []      # No tables
            mock_document.return_value = mock_doc
            
            mock_file.read = AsyncMock(return_value=b"mock_content")
            
            with pytest.raises(Exception):  # Should raise HTTPException for empty content
                await DocxService.extract_text_from_docx(mock_file)
    
    @pytest.mark.asyncio
    async def test_extract_text_from_docx_with_content(self):
        """Test DOCX text extraction with actual content"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.docx"
        
        # Mock the docx.Document to return sample content
        with patch('service.docx_service.Document') as mock_document:
            mock_doc = Mock()
            
            # Mock paragraphs
            mock_paragraph1 = Mock()
            mock_paragraph1.text = "First paragraph content."
            mock_paragraph2 = Mock()
            mock_paragraph2.text = "Second paragraph content."
            mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
            
            # Mock empty tables
            mock_doc.tables = []
            
            mock_document.return_value = mock_doc
            mock_file.read = AsyncMock(return_value=b"mock_content")
            
            result = await DocxService.extract_text_from_docx(mock_file)
            
            assert "First paragraph content." in result
            assert "Second paragraph content." in result
    
    @pytest.mark.asyncio
    async def test_extract_text_from_docx_with_tables(self):
        """Test DOCX text extraction with tables"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.docx"
        
        with patch('service.docx_service.Document') as mock_document:
            mock_doc = Mock()
            
            # Mock empty paragraphs
            mock_doc.paragraphs = []
            
            # Mock table content
            mock_cell1 = Mock()
            mock_cell1.text = "Cell 1"
            mock_cell2 = Mock()
            mock_cell2.text = "Cell 2"
            
            mock_row = Mock()
            mock_row.cells = [mock_cell1, mock_cell2]
            
            mock_table = Mock()
            mock_table.rows = [mock_row]
            
            mock_doc.tables = [mock_table]
            
            mock_document.return_value = mock_doc
            mock_file.read = AsyncMock(return_value=b"mock_content")
            
            result = await DocxService.extract_text_from_docx(mock_file)
            
            assert "--- Table 1 ---" in result
            assert "Cell 1 | Cell 2" in result


class TestDocxAgentExecutionModels:
    """Test cases for DOCX agent execution models"""
    
    def test_docx_agent_execution_request_validation(self):
        """Test DOCX agent execution request model validation"""
        # Valid request
        request_data = {
            "agent_name": "test-agent",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": "test-user-123",
            "chunk_size": 4000
        }
        request = DocxAgentExecutionRequest(**request_data)
        assert request.agent_name == "test-agent"
        assert request.chunk_size == 4000
    
    def test_docx_agent_execution_request_default_chunk_size(self):
        """Test DOCX agent execution request with default chunk size"""
        request_data = {
            "agent_name": "test-agent",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": "test-user-123"
        }
        request = DocxAgentExecutionRequest(**request_data)
        assert request.chunk_size == 4000  # Default value
    
    def test_docx_agent_execution_request_with_parameters(self):
        """Test DOCX agent execution request with parameters"""
        request_data = {
            "agent_name": "test-agent",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": "test-user-123",
            "parameters": {"param1": "value1", "param2": "value2"}
        }
        request = DocxAgentExecutionRequest(**request_data)
        assert request.parameters == {"param1": "value1", "param2": "value2"}
    
    def test_docx_agent_execution_response_creation(self):
        """Test DOCX agent execution response model creation"""
        response_data = {
            "job_id": "job-123",
            "agent": "test-agent",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "status": "completed",
            "result": "Analysis complete",
            "chunks_processed": 3,
            "docx_filename": "test.docx"
        }
        response = DocxAgentExecutionResponse(**response_data)
        assert response.job_id == "job-123"
        assert response.chunks_processed == 3
        assert response.docx_filename == "test.docx"
        assert response.status == "completed"
    
    def test_docx_agent_execution_request_validation_errors(self):
        """Test DOCX agent execution request validation errors"""
        # Test empty agent_name
        with pytest.raises(ValueError):
            DocxAgentExecutionRequest(
                agent_name="",
                provider="openai",
                model="gpt-3.5-turbo",
                user_id="test-user"
            )
        
        # Test too long agent_name
        with pytest.raises(ValueError):
            DocxAgentExecutionRequest(
                agent_name="a" * 101,  # Exceeds 100 character limit
                provider="openai",
                model="gpt-3.5-turbo",
                user_id="test-user"
            )
        
        # Test empty provider
        with pytest.raises(ValueError):
            DocxAgentExecutionRequest(
                agent_name="test-agent",
                provider="",
                model="gpt-3.5-turbo",
                user_id="test-user"
            )


if __name__ == "__main__":
    pytest.main([__file__])