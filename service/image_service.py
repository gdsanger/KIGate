"""
Image Service for handling image files and converting them to base64
"""
import logging
import base64
from typing import List
from fastapi import UploadFile, HTTPException
import io

logger = logging.getLogger(__name__)


class ImageService:
    """Service for handling image operations"""
    
    # Supported image MIME types
    SUPPORTED_IMAGE_TYPES = {
        'image/png',
        'image/jpeg',
        'image/jpg',
        'image/webp'
    }
    
    @staticmethod
    async def convert_image_to_base64(image_file: UploadFile) -> str:
        """
        Convert an image file to base64 encoded string
        
        Args:
            image_file: UploadFile object containing image data
            
        Returns:
            str: Base64 encoded image data
            
        Raises:
            HTTPException: If image cannot be processed
        """
        try:
            # Read the file content
            content = await image_file.read()
            
            # Validate content size (limit to 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if len(content) > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image file too large. Maximum size is {max_size / (1024*1024):.1f}MB"
                )
            
            # Convert to base64
            base64_image = base64.b64encode(content).decode('utf-8')
            
            logger.info(f"Successfully converted image '{image_file.filename}' to base64 (size: {len(content)} bytes)")
            
            return base64_image
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process image: {str(e)}"
            )
    
    @staticmethod
    def validate_image_type(content_type: str, filename: str) -> bool:
        """
        Validate if the uploaded file is a supported image type
        
        Args:
            content_type: MIME type of the file
            filename: Name of the file
            
        Returns:
            bool: True if valid image type
            
        Raises:
            HTTPException: If image type is not supported
        """
        # Check MIME type
        if content_type and content_type.lower() in ImageService.SUPPORTED_IMAGE_TYPES:
            return True
        
        # Check file extension as fallback
        if filename:
            lower_filename = filename.lower()
            if any(lower_filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                return True
        
        # Raise error if not supported
        supported_formats = ', '.join([ext.replace('image/', '') for ext in ImageService.SUPPORTED_IMAGE_TYPES])
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format. Supported formats: {supported_formats}"
        )
