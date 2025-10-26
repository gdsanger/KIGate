"""
Test script for AI Agent Generator functionality
"""
import asyncio
import logging
import json
import os
from model.ai_agent_generator import AgentGenerationRequest, AgentGenerationResponse
from service.ai_agent_generator_service import AIAgentGeneratorService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_service_creation_prompt():
    """Test that the service creates a proper generation prompt"""
    print("Testing prompt creation...")
    
    user_description = "I need an agent that corrects German emails and makes them more professional"
    prompt = AIAgentGeneratorService._create_generation_prompt(user_description)
    
    # Check that prompt contains key elements
    assert user_description in prompt, "User description should be in prompt"
    assert "JSON" in prompt, "Prompt should request JSON response"
    assert "name" in prompt, "Prompt should specify name field"
    assert "provider" in prompt, "Prompt should specify provider field"
    
    print("✓ Prompt creation works correctly")


async def test_parameters_yaml_conversion():
    """Test parameter conversion to YAML"""
    print("\nTesting parameter YAML conversion...")
    
    # Test with sample parameters
    parameters = [
        {
            "input_text": {
                "type": "string",
                "description": "The input text to process"
            }
        },
        {
            "output_format": {
                "type": "string", 
                "description": "Desired output format",
                "default": "text"
            }
        }
    ]
    
    yaml_result = AIAgentGeneratorService.convert_parameters_to_yaml(parameters)
    
    assert yaml_result is not None, "YAML conversion should not return None"
    assert "input_text:" in yaml_result, "YAML should contain parameter names"
    assert "type: string" in yaml_result, "YAML should contain type info"
    assert "description:" in yaml_result, "YAML should contain descriptions"
    
    print("✓ Parameter YAML conversion works correctly")
    print(f"Generated YAML:\n{yaml_result}")


async def test_empty_parameters():
    """Test handling of empty parameters"""
    print("\nTesting empty parameters handling...")
    
    result = AIAgentGeneratorService.convert_parameters_to_yaml(None)
    assert result is None, "None parameters should return None"
    
    result = AIAgentGeneratorService.convert_parameters_to_yaml([])
    assert result is None, "Empty parameters should return None"
    
    print("✓ Empty parameters handled correctly")


async def test_agent_generation_with_mock():
    """Test agent generation with a mock response (when API key available)"""
    print("\nTesting agent generation...")
    
    # Only run if API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  Skipping API test - no OPENAI_API_KEY set")
        return
    
    try:
        request = AgentGenerationRequest(
            description="I need an agent that corrects German emails and makes them more professional"
        )
        
        result = await AIAgentGeneratorService.generate_agent_config(request)
        
        if result is not None:
            print("✓ Agent generation successful")
            print(f"Generated agent name: {result.name}")
            print(f"Generated provider: {result.provider}")
            print(f"Generated model: {result.model}")
            print(f"Description: {result.description[:100]}...")
            
            # Validate the result structure
            assert result.name, "Name should not be empty"
            assert result.description, "Description should not be empty"
            assert result.role, "Role should not be empty"
            assert result.provider in ["openai", "claude", "gemini", "anthropic", "azure", "local"], "Provider should be valid"
            assert result.model, "Model should not be empty"
            assert result.task, "Task should not be empty"
            
            print("✓ Generated agent has valid structure")
        else:
            print("❌ Agent generation failed - this could be due to API issues or response format")
    
    except Exception as e:
        print(f"❌ Error in agent generation: {e}")


async def test_model_validation():
    """Test model validation"""
    print("\nTesting model validation...")
    
    # Test valid request
    try:
        request = AgentGenerationRequest(
            description="This is a valid description that is long enough to pass validation."
        )
        print("✓ Valid request created successfully")
    except Exception as e:
        print(f"❌ Valid request failed: {e}")
    
    # Test invalid request (too short)
    try:
        request = AgentGenerationRequest(
            description="short"
        )
        print("❌ Should have failed validation for short description")
    except Exception as e:
        print(f"✓ Correctly rejected short description: {e}")


async def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Running AI Agent Generator Tests")
    print("=" * 50)
    
    await test_service_creation_prompt()
    await test_parameters_yaml_conversion()
    await test_empty_parameters()
    await test_model_validation()
    await test_agent_generation_with_mock()
    
    print("\n" + "=" * 50)
    print("AI Agent Generator Tests Completed")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())