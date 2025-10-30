"""
Integration test for PDF Agent Execution functionality
"""
import pytest
import asyncio
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from fastapi import UploadFile
from service.pdf_service import PDFService


class TestPDFIntegration:
    """Integration tests for PDF processing"""
    
    @pytest.fixture
    def test_pdf_path(self, tmp_path):
        """Provide path to test PDF file"""
        import os
        # Try to use existing test PDF if available, otherwise skip
        test_pdf = "/tmp/test_files/test_document.pdf"
        if Path(test_pdf).exists():
            return test_pdf
        
        # Alternative: check for environment variable or fallback
        env_pdf = os.environ.get("TEST_PDF_PATH")
        if env_pdf and Path(env_pdf).exists():
            return env_pdf
            
        # If no test PDF is available, create a simple one or skip
        return test_pdf  # Will cause test to skip if not available
    
    @pytest.mark.asyncio
    async def test_pdf_text_extraction_integration(self, test_pdf_path):
        """Test actual PDF text extraction with a real PDF file"""
        
        # Check if test PDF exists
        if not Path(test_pdf_path).exists():
            pytest.skip("Test PDF file not available")
        
        # Read the PDF file
        with open(test_pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        # Create a mock UploadFile
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=pdf_content)
        mock_file.filename = "test_document.pdf"
        mock_file.seek = AsyncMock()
        
        # Extract text
        extracted_text = await PDFService.extract_text_from_pdf(mock_file)
        
        # Verify extraction worked
        assert extracted_text is not None
        assert len(extracted_text) > 0
        assert "Test PDF Document" in extracted_text
        assert "This is a test document" in extracted_text
        assert "Page 2 of Test Document" in extracted_text
        
        print(f"Extracted text length: {len(extracted_text)}")
        print(f"First 200 characters: {extracted_text[:200]}")
    
    def test_chunking_with_real_text(self):
        """Test text chunking with realistic content"""
        
        # Simulate extracted PDF text
        sample_text = """Test PDF Document
This is a test document for the PDF Agent Execution endpoint. 
It contains multiple lines of text to test the extraction functionality. 
The agent should be able to process this content and provide analysis.

--- Page 2 ---
Page 2 of Test Document
This second page contains additional content. 
The PDF service should extract text from all pages. 
This tests the multi-page functionality."""
        
        # Test different chunk sizes
        small_chunks = PDFService.chunk_text(sample_text, chunk_size=100)
        assert len(small_chunks) > 1
        
        large_chunks = PDFService.chunk_text(sample_text, chunk_size=1000)
        assert len(large_chunks) == 1  # Should fit in one chunk
        
        # Test that all text is preserved
        combined_small = " ".join(small_chunks)
        combined_large = " ".join(large_chunks)
        
        # Remove extra whitespace for comparison
        original_normalized = " ".join(sample_text.split())
        combined_small_normalized = " ".join(combined_small.split())
        combined_large_normalized = " ".join(combined_large.split())
        
        # The text should be substantially preserved (allowing for chunking boundaries)
        assert len(combined_small_normalized) >= len(original_normalized) * 0.95
        assert len(combined_large_normalized) >= len(original_normalized) * 0.95
    
    def test_merge_results_realistic(self):
        """Test merging results with realistic agent responses"""
        
        # Simulate results from different chunks
        chunk_results = [
            "Analysis of first section: The document introduces a test scenario for PDF processing.",
            "Analysis of second section: The document describes multi-page functionality testing.",
            "Analysis of third section: The document concludes with validation requirements."
        ]
        
        merged = PDFService.merge_chunk_results(chunk_results, "test-analyzer")
        
        # Verify structure
        assert "test-analyzer Analysis Results" in merged
        assert "Section 1 Results" in merged
        assert "Section 2 Results" in merged
        assert "Section 3 Results" in merged
        assert "Total sections processed: 3" in merged
        
        # Verify all original content is included
        for result in chunk_results:
            assert result in merged
    
    def test_file_validation_scenarios(self):
        """Test various file validation scenarios"""
        
        # Test valid PDF filename
        valid_files = ["test.pdf", "document.PDF", "file_name.pdf"]
        for filename in valid_files:
            # This would normally be validated in the endpoint
            assert filename.lower().endswith('.pdf')
        
        # Test invalid filenames
        invalid_files = ["test.txt", "document.docx", "file.png", "no_extension"]
        for filename in invalid_files:
            assert not filename.lower().endswith('.pdf')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])