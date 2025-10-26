"""
GitHub Issue Processor Service for improving text and generating issue metadata
"""
import json
import logging
import uuid
from typing import Optional
from model.github_issue import ProcessedIssueContent, IssueType
from model.aiapirequest import aiapirequest
from service.ai_service import send_ai_request

logger = logging.getLogger(__name__)

class GitHubIssueProcessor:
    """Service for processing text into improved GitHub issues using AI"""
    
    # System prompt for text improvement and issue categorization
    SYSTEM_PROMPT = """You are an expert GitHub issue processor. Your task is to:

1. Improve the provided text for spelling, grammar, and clarity
2. Make the text structured and machine-readable
3. Generate a clear, specific title (max 80 characters)
4. Classify the issue type as: bug, enhancement, or task
5. Suggest relevant labels

Return your response in this exact JSON format:
{
    "improved_text": "The improved and structured issue description",
    "title": "Clear Issue Title",
    "issue_type": "bug|enhancement|task",
    "labels": ["label1", "label2"]
}

Guidelines:
- For bug reports: Include steps to reproduce, expected behavior, actual behavior
- For features: Include clear use case, acceptance criteria
- For tasks: Include clear objectives and requirements
- Use markdown formatting in improved_text for better readability
- Keep titles concise but descriptive
- Suggest 1-3 relevant labels based on content

Input text to process:"""

    @staticmethod
    async def process_issue_text(
        text: str, 
        user_id: str, 
        provider: str = "openai",
        model: str = "gpt-3.5-turbo"
    ) -> Optional[ProcessedIssueContent]:
        """
        Process raw text into improved GitHub issue content
        
        Args:
            text: Raw input text
            user_id: User ID for tracking
            provider: AI provider to use
            model: AI model to use
            
        Returns:
            ProcessedIssueContent or None if processing fails
        """
        try:
            # Create AI request
            job_id = str(uuid.uuid4())
            combined_prompt = f"{GitHubIssueProcessor.SYSTEM_PROMPT}\n\n{text}"
            
            ai_request = aiapirequest(
                job_id=job_id,
                user_id=user_id,
                model=model,
                message=combined_prompt
            )
            
            # Send to AI service
            result = await send_ai_request(ai_request, provider)
            
            if not result.success:
                return None
            
            # Parse AI response
            try:
                # Try to extract JSON from the response
                response_text = result.content.strip()
                
                # Handle case where AI might wrap JSON in code blocks
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                
                # Parse JSON
                parsed_response = json.loads(response_text)
                
                # Validate required fields
                if not all(key in parsed_response for key in ["improved_text", "title", "issue_type"]):
                    return None
                
                # Map issue type string to enum
                issue_type_str = parsed_response["issue_type"].lower()
                if issue_type_str == "bug":
                    issue_type = IssueType.BUG
                elif issue_type_str == "enhancement":
                    issue_type = IssueType.FEATURE
                elif issue_type_str == "task":
                    issue_type = IssueType.TASK
                else:
                    # Default to task if unknown
                    issue_type = IssueType.TASK
                
                # Create processed content
                return ProcessedIssueContent(
                    improved_text=parsed_response["improved_text"],
                    title=parsed_response["title"][:80],  # Limit title length
                    issue_type=issue_type,
                    labels=parsed_response.get("labels", [])
                )
                
            except json.JSONDecodeError:
                # Fallback: try to extract information manually
                return GitHubIssueProcessor._fallback_processing(text, result.content)
                
        except Exception as e:
            # Log error and return None
            logger.error(f"Error processing issue text: {str(e)}")
            return None
    
    @staticmethod
    def _fallback_processing(original_text: str, ai_response: str) -> Optional[ProcessedIssueContent]:
        """
        Fallback processing when JSON parsing fails
        
        Args:
            original_text: Original input text
            ai_response: AI response that couldn't be parsed as JSON
            
        Returns:
            ProcessedIssueContent with basic improvements or None
        """
        try:
            # Use AI response as improved text, generate basic title and type
            improved_text = ai_response if ai_response else original_text
            
            # Generate basic title from first line or sentence
            title_words = original_text.split()[:10]
            title = " ".join(title_words)
            if len(title) > 80:
                title = title[:77] + "..."
            
            # Basic issue type detection
            text_lower = original_text.lower()
            if any(word in text_lower for word in ["bug", "error", "fix", "broken", "issue"]):
                issue_type = IssueType.BUG
            elif any(word in text_lower for word in ["feature", "add", "new", "enhance", "improve"]):
                issue_type = IssueType.FEATURE
            else:
                issue_type = IssueType.TASK
            
            return ProcessedIssueContent(
                improved_text=improved_text,
                title=title,
                issue_type=issue_type,
                labels=[]
            )
            
        except Exception as e:
            logger.error(f"Error in fallback processing: {str(e)}")
            return None