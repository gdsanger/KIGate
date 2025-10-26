"""
AI Agent Generator Service
Handles generating agent configurations using OpenAI API
"""
import json
import logging
import yaml
from typing import Optional
import uuid

from model.ai_agent_generator import AgentGenerationRequest, AgentGenerationResponse
from model.aiapirequest import aiapirequest
from controller.api_openai import process_openai_request

logger = logging.getLogger(__name__)


class AIAgentGeneratorService:
    """Service for generating agent configurations using AI"""
    
    # Configuration constants
    DEFAULT_AI_MODEL = "gpt-4"  # Model used for agent generation
    MAX_JSON_RESPONSE_SIZE = 50000  # 50KB limit for JSON response
    
    @staticmethod
    def _create_generation_prompt(user_description: str) -> str:
        """Create a structured prompt for agent generation"""
        return f"""You are an expert AI assistant specializing in creating AI agent configurations. Based on the user's description, generate a complete agent configuration.

User Description: "{user_description}"

Please generate a JSON response with the following structure. Be specific and practical:

{{
    "name": "agent-name-kebab-case",
    "description": "A concise but informative description (50-200 characters)",
    "role": "Define the agent's role and expertise in 1-2 sentences",
    "provider": "openai|claude|gemini (recommend the most suitable)",
    "model": "specific-model-name (e.g., gpt-4, claude-3-sonnet, gemini-pro)",
    "task": "Detailed task instructions that will be used as the system prompt. Be specific about what the agent should do, how it should respond, and any constraints or guidelines.",
    "parameters": [
        {{
            "input_text": {{
                "type": "string",
                "description": "The main input text to process"
            }}
        }},
        {{
            "output_format": {{
                "type": "string", 
                "description": "Desired output format",
                "default": "text"
            }}
        }}
    ],
    "confidence_score": 0.85
}}

Guidelines:
- Choose the name carefully: use kebab-case, be descriptive but concise
- The role should establish the agent's expertise and personality
- The task should be detailed and actionable - this becomes the system prompt
- Recommend the AI provider best suited for this type of task
- Include realistic parameters that users might want to configure
- Only respond with valid JSON, no additional text"""
    
    @classmethod
    async def generate_agent_config(cls, request: AgentGenerationRequest) -> Optional[AgentGenerationResponse]:
        """Generate agent configuration using OpenAI API"""
        try:
            logger.info(f"Generating agent config for description: {request.description[:100]}...")
            
            # Create the AI request
            prompt = cls._create_generation_prompt(request.description)
            ai_request = aiapirequest(
                job_id=str(uuid.uuid4()),
                user_id="ai-agent-generator",
                model=cls.DEFAULT_AI_MODEL,  # Use configured model for better structured output
                message=prompt
            )
            
            # Send request to OpenAI
            result = await process_openai_request(ai_request)
            
            if not result.success:
                logger.error(f"OpenAI request failed: {result.error_message}")
                return None
            
            # Parse the JSON response with validation
            try:
                response_content = result.content.strip()
                # Validate response size to prevent JSON bombs
                if len(response_content) > cls.MAX_JSON_RESPONSE_SIZE:
                    logger.error(f"AI response too large: {len(response_content)} bytes")
                    return None
                
                generated_config = json.loads(response_content)
                logger.info("Successfully parsed AI-generated config")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"AI Response content: {result.content[:500]}...")  # Log only first 500 chars
                return None
            
            # Validate and create response
            try:
                response = AgentGenerationResponse(**generated_config)
                logger.info(f"Generated agent config: {response.name}")
                return response
            except Exception as e:
                logger.error(f"Failed to create AgentGenerationResponse: {e}")
                logger.debug(f"Generated config: {generated_config}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error in agent generation: {e}")
            return None
    
    @staticmethod
    def convert_parameters_to_yaml(parameters: Optional[list]) -> Optional[str]:
        """Convert parameters list to YAML string format for the form"""
        if not parameters:
            return None
            
        try:
            # Convert the parameters to the expected YAML format
            yaml_data = []
            for param_dict in parameters:
                for param_name, param_config in param_dict.items():
                    yaml_entry = {param_name: param_config}
                    yaml_data.append(yaml_entry)
            
            return yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True, indent=2)
        except Exception as e:
            logger.error(f"Failed to convert parameters to YAML: {e}")
            return None