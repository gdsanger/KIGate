# Claude API Controller Documentation

## Overview

The Claude API controller encapsulates the Anthropic Claude API functionality and provides a standardized interface for making AI requests. It accepts `aiapirequest` objects and returns `aiapiresult` objects with comprehensive error handling.

## Configuration

### Environment Variables

Set the following environment variables in your `.env` file:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Required Dependencies

The controller requires the `anthropic` package, which is included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## API Endpoint

### POST /api/claude

Processes AI requests using Anthropic Claude models.

**Authentication**: Bearer token required (client_id:client_secret)

**Request Body**:
```json
{
  "job_id": "unique-job-identifier",
  "user_id": "user-identifier", 
  "model": "claude-3-haiku-20240307",
  "message": "Your prompt message for the AI"
}
```

**Response**:
```json
{
  "job_id": "unique-job-identifier",
  "user_id": "user-identifier",
  "content": "AI response content",
  "success": true,
  "error_message": null
}
```

**Error Response**:
```json
{
  "job_id": "unique-job-identifier", 
  "user_id": "user-identifier",
  "content": "",
  "success": false,
  "error_message": "Error description"
}
```

## Supported Models

The controller supports various Claude models:
- `claude-3-5-sonnet-20241022` (latest Sonnet model)
- `claude-3-5-sonnet-20240620` (previous Sonnet model)
- `claude-3-opus-20240229` (most capable model)
- `claude-3-sonnet-20240229` (balanced performance)
- `claude-3-haiku-20240307` (fastest model)
- Other available Claude models

The controller does not have a default fallback model, so a valid model must be specified.

## Usage Examples

### Using curl

```bash
# First, get an API key from the admin panel or create a user
# Then use the client_id:client_secret as Bearer token

curl -X POST "http://localhost:8000/api/claude" \
  -H "Authorization: Bearer your_client_id:your_client_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "user_id": "user-456", 
    "model": "claude-3-haiku-20240307",
    "message": "Hello, how are you today?"
  }'
```

### Using Python

```python
import httpx
import asyncio

async def call_claude_api():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/claude",
            json={
                "job_id": "job-123",
                "user_id": "user-456",
                "model": "claude-3-haiku-20240307",
                "message": "Hello, how are you today?"
            },
            headers={
                "Authorization": "Bearer client_id:client_secret",
                "Content-Type": "application/json"
            }
        )
        
        result = response.json()
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Response: {result['content']}")
        else:
            print(f"Error: {result['error_message']}")

asyncio.run(call_claude_api())
```

### Using the Controller Directly

```python
from model.aiapirequest import aiapirequest
from controller.api_claude import process_claude_request
import asyncio

async def direct_usage():
    request = aiapirequest(
        job_id="job-123",
        user_id="user-456",
        model="claude-3-haiku-20240307",
        message="Hello, how are you today?"
    )
    
    result = await process_claude_request(request)
    
    print(f"Success: {result.success}")
    if result.success:
        print(f"Response: {result.content}")
    else:
        print(f"Error: {result.error_message}")

asyncio.run(direct_usage())
```

## Error Handling

The controller implements comprehensive error handling:

### Configuration Errors
- **Missing API Key**: Returns error when `ANTHROPIC_API_KEY` is not configured
- **Invalid Configuration**: Returns error when API client initialization fails

### Validation Errors  
- **Empty Message**: Returns error when the message field is empty
- **Empty Model**: Returns error when the model field is empty

### API Errors
- **Rate Limiting**: Detects and reports rate limit exceeded errors
- **Authentication**: Detects and reports authentication/permission errors  
- **API Errors**: Catches and reports other Claude API errors
- **Unexpected Errors**: Catches and reports any unexpected errors

### Example Error Responses

**Missing API Key**:
```json
{
  "job_id": "job-123",
  "user_id": "user-456", 
  "content": "",
  "success": false,
  "error_message": "Anthropic API key is not configured"
}
```

**Empty Message**:
```json
{
  "job_id": "job-123",
  "user_id": "user-456",
  "content": "",
  "success": false, 
  "error_message": "Message cannot be empty"
}
```

**Rate Limit Error**:
```json
{
  "job_id": "job-123",
  "user_id": "user-456",
  "content": "",
  "success": false,
  "error_message": "Claude API rate limit exceeded: ..."
}
```

**Authentication Error**:
```json
{
  "job_id": "job-123",
  "user_id": "user-456",
  "content": "",
  "success": false,
  "error_message": "Claude API authentication failed: ..."
}
```

## Configuration Parameters

The Claude controller uses the following default configuration:

- **Max Tokens**: 1000 (configurable via `DEFAULT_MAX_TOKENS`)
- **Message Format**: Single user message (no system message support in current implementation)
- **Temperature**: Uses Claude API defaults (not explicitly set)

## Logging

The controller provides detailed logging at different levels:

- **INFO**: Successful operations, request processing, controller initialization
- **WARNING**: Non-critical issues (currently minimal)  
- **ERROR**: Configuration issues, validation errors, API errors
- **DEBUG**: Detailed API request information

## Testing

Run the Claude controller tests:

```bash
python -m pytest test_claude_controller.py -v
```

Or run the standalone test script:

```bash
python test_claude_controller.py
```

The test suite includes:
- Configuration validation (missing API keys)
- Input validation (empty message, empty model)
- Error handling with fake API keys
- Authentication error scenarios

## Security Considerations

1. **API Key Security**: Never expose your `ANTHROPIC_API_KEY` in code or logs
2. **Authentication**: All endpoints require proper Bearer token authentication
3. **Input Validation**: All inputs are validated before processing
4. **Error Information**: Error messages don't expose sensitive configuration details

## Comparison with Other Controllers

| Feature | Claude Controller | Gemini Controller | OpenAI Controller |
|---------|------------------|-------------------|-------------------|
| Input Field | `message` | `message` | `prompt` + `role` |
| Default Model | None | `gemini-pro` | No default |
| Model Fallback | No | Yes (to gemini-pro) | No |
| API Library | `anthropic` | `google-generativeai` | `openai` |
| Authentication | API Key | API Key | API Key + Optional Org ID |
| Max Tokens | 1000 (default) | API defaults | API defaults |

## Troubleshooting

### Common Issues

1. **"Anthropic API key is not configured"**
   - Ensure `ANTHROPIC_API_KEY` is set in your `.env` file
   - Verify the `.env` file is in the correct directory
   - Restart the application after adding the key

2. **"Message cannot be empty" or "Model cannot be empty"**
   - Check that both `message` and `model` fields are provided
   - Ensure the fields contain non-empty strings

3. **Authentication errors**
   - Verify your Anthropic API key is valid and active
   - Check if your account has proper permissions and credits
   - Ensure you're using the correct API key format

4. **Rate limit errors**  
   - Implement retry logic with exponential backoff
   - Check your API quota and usage limits in the Anthropic console
   - Consider using different models (e.g., Haiku for faster, cheaper requests)

5. **Model not found errors**
   - Verify the model name is correct and available
   - Check Anthropic's documentation for available models
   - Ensure your API key has access to the requested model

### Debug Mode

Enable debug logging to see detailed request information:

```python
import logging
logging.getLogger("controller.api_claude").setLevel(logging.DEBUG)
```

### Getting Help

For issues specific to the KIGate implementation, check the logs for detailed error information. For Claude API issues, refer to the [Anthropic Claude API documentation](https://docs.anthropic.com/claude/reference).

## API Limits and Best Practices

1. **Rate Limits**: Claude API has rate limits that vary by model and subscription tier
2. **Token Limits**: Current implementation uses 1000 max tokens - adjust `DEFAULT_MAX_TOKENS` if needed
3. **Cost Optimization**: Use Claude Haiku for simple tasks, Sonnet for balanced needs, Opus for complex reasoning
4. **Error Handling**: Always check the `success` field in responses before using `content`