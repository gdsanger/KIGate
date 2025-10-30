"""
PDF Service for extracting text content from PDF files
"""
import logging
import pypdf
from typing import List, BinaryIO
from fastapi import UploadFile, HTTPException
import io

logger = logging.getLogger(__name__)


class PDFService:
    """Service for handling PDF operations"""
    
    @staticmethod
    async def extract_text_from_pdf(pdf_file: UploadFile) -> str:
        """
        Extract text content from a PDF file
        
        Args:
            pdf_file: UploadFile object containing PDF data
            
        Returns:
            str: Extracted text content from all pages
            
        Raises:
            HTTPException: If PDF cannot be processed
        """
        try:
            # Read the file content
            content = await pdf_file.read()
            
            # Create a file-like object from the bytes
            pdf_stream = io.BytesIO(content)
            
            # Create PDF reader
            pdf_reader = pypdf.PdfReader(pdf_stream)
            
            # Extract text from all pages
            text_content = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():  # Only add non-empty pages
                        text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                except Exception as page_error:
                    logger.warning(f"Could not extract text from page {page_num + 1}: {str(page_error)}")
                    continue
            
            if not text_content:
                raise HTTPException(
                    status_code=400,
                    detail="No text content could be extracted from the PDF file"
                )
            
            # Join all pages with double newline
            full_text = "\n\n".join(text_content)
            
            logger.info(f"Successfully extracted {len(full_text)} characters from PDF with {len(pdf_reader.pages)} pages")
            
            return full_text
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process PDF file: {str(e)}"
            )
        finally:
            # Reset file pointer for potential reuse
            try:
                if hasattr(pdf_file, 'seek'):
                    await pdf_file.seek(0)
                elif hasattr(pdf_file, 'file') and hasattr(pdf_file.file, 'seek'):
                    pdf_file.file.seek(0)
            except Exception:
                pass  # Ignore errors during cleanup
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks with optional overlap for better context preservation
        
        Args:
            text: Input text to chunk
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List[str]: List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to break at a sentence or paragraph boundary near the end
            if end < len(text):
                # Look for sentence endings within the last 10% of the chunk
                search_start = max(start, end - chunk_size // 10)
                
                # Look for paragraph breaks first (double newline)
                paragraph_break = text.rfind('\n\n', search_start, end)
                if paragraph_break > search_start:
                    end = paragraph_break + 2
                else:
                    # Look for sentence endings
                    sentence_break = max(
                        text.rfind('. ', search_start, end),
                        text.rfind('.\n', search_start, end),
                        text.rfind('! ', search_start, end),
                        text.rfind('?\n', search_start, end)
                    )
                    if sentence_break > search_start:
                        end = sentence_break + 2
                    # Otherwise use the character limit
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
        
        logger.info(f"Split text into {len(chunks)} chunks of average size {len(text) // len(chunks) if chunks else 0}")
        
        return chunks
    
    @staticmethod
    def merge_chunk_results(chunk_results: List[str], agent_name: str) -> str:
        """
        Merge results from multiple text chunks into a coherent final result
        
        Args:
            chunk_results: List of results from processing individual chunks
            agent_name: Name of the agent for context
            
        Returns:
            str: Merged result
        """
        if not chunk_results:
            return "No results to merge."
        
        if len(chunk_results) == 1:
            return chunk_results[0]
        
        # Create a structured summary format
        merged_result = f"# {agent_name} Analysis Results\n\n"
        merged_result += f"This document was processed in {len(chunk_results)} parts. Below are the consolidated results:\n\n"
        
        for i, result in enumerate(chunk_results, 1):
            merged_result += f"## Section {i} Results\n\n{result}\n\n"
        
        # Add a brief summary if we have multiple sections
        if len(chunk_results) > 2:
            merged_result += "## Overall Summary\n\n"
            merged_result += "The document has been analyzed in multiple sections. "
            merged_result += "Please review each section above for detailed findings. "
            merged_result += f"Total sections processed: {len(chunk_results)}\n"
        
        return merged_result