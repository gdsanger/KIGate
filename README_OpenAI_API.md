# OpenAI API Controller Documentation

This document describes how to use the OpenAI API controller implemented in `/controller/api_openai.py`.

## Overview

The OpenAI API controller encapsulates the OpenAI API functionality and provides a standardized interface for making AI requests. It accepts `aiapirequest` objects and returns `aiapiresult` objects with comprehensive error handling.

## Configuration

### Environment Variables

Set the following environment variables in your `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ORG_ID=your_organization_id_here  # Optional
```

### Required Dependencies

The controller requires the `openai` package, which is included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## API Endpoint

### POST /api/openai

**Authentication**: Bearer Token (required)

**Request Body**: `aiapirequest` object

```json
{
  "job_id": "string",
  "user_id": "string", 
  "model": "string",
  "role": "string",
  "prompt": "string"
}
```

**Response**: `aiapiresult` object

```json
{
  "job_id": "string",
  "user_id": "string",
  "content": "string",
  "success": boolean,
  "error_message": "string | null"
}
```

## Usage Examples

### Using curl

```bash
# First, get an API key from the admin panel or create a user
# Then use the client_id:client_secret as Bearer token

curl -X POST "http://localhost:8000/api/openai" \
  -H "Authorization: Bearer your_client_id:your_client_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "user_id": "user-456", 
    "model": "gpt-3.5-turbo",
    "role": "user",
    "prompt": "Hello, how are you today?"
  }'
```

### Using Python

```python
import httpx
import asyncio

async def call_openai_api():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/openai",
            json={
                "job_id": "job-123",
                "user_id": "user-456",
                "model": "gpt-3.5-turbo", 
                "role": "user",
                "prompt": "Hello, how are you today?"
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

asyncio.run(call_openai_api())
```

### Using the Controller Directly

```python
from model.aiapirequest import aiapirequest
from controller.api_openai import process_openai_request
import asyncio

async def direct_usage():
    request = aiapirequest(
        job_id="job-123",
        user_id="user-456",
        model="gpt-3.5-turbo",
        role="user", 
        prompt="Hello, how are you today?"
    )
    
    result = await process_openai_request(request)
    
    print(f"Success: {result.success}")
    if result.success:
        print(f"Response: {result.content}")
    else:
        print(f"Error: {result.error_message}")

asyncio.run(direct_usage())
```

## Request Parameters

### Required Fields

- `job_id`: Unique identifier for the job (preserved in response)
- `user_id`: User identifier (preserved in response)  
- `model`: OpenAI model to use (e.g., "gpt-3.5-turbo", "gpt-4")
- `role`: Message role ("system", "user", or "assistant")
- `prompt`: The message content to send to OpenAI

### Supported Models

The controller supports all OpenAI chat completion models:
- `gpt-3.5-turbo`
- `gpt-4`
- `gpt-4-turbo`
- `gpt-4o`
- And other available models

### Supported Roles

- `system`: System message (sets behavior)
- `user`: User message (default fallback)
- `assistant`: Assistant message

Invalid roles will default to `user` with a warning logged.

## Response Format

### Success Response

```json
{
  "job_id": "job-123",
  "user_id": "user-456",
  "content": "Hello! I'm doing well, thank you for asking. How can I help you today?",
  "success": true,
  "error_message": null
}
```

### Error Response

```json
{
  "job_id": "job-123", 
  "user_id": "user-456",
  "content": "",
  "success": false,
  "error_message": "OpenAI API authentication failed: Invalid API key"
}
```

## Error Handling

The controller provides comprehensive error handling for:

### Configuration Errors
- Missing or invalid OpenAI API key
- Invalid organization ID

### Validation Errors  
- Empty prompt
- Empty model name

### OpenAI API Errors
- **Authentication Error**: Invalid API key or organization
- **Rate Limit Error**: API quota exceeded
- **API Error**: General OpenAI API errors

### Network Errors
- Connection timeouts
- Network connectivity issues

## Logging

The controller logs important events:

- **INFO**: Successful requests and controller initialization
- **WARNING**: Invalid roles, missing configuration
- **ERROR**: Authentication failures, API errors, validation failures
- **DEBUG**: API request details

## Testing

Run the test suite to validate functionality:

```bash
# Unit tests
python test_openai_controller.py

# Integration tests (requires running server)
python main.py &  # Start server
python test_openai_integration.py
```

## Security Considerations

1. **API Key Protection**: Never expose OpenAI API keys in client-side code
2. **Authentication Required**: All endpoint access requires valid Bearer tokens
3. **Input Validation**: All inputs are validated before processing
4. **Error Message Safety**: Error messages don't expose sensitive information

## Performance Notes

- Uses `AsyncOpenAI` client for optimal async performance
- Singleton pattern for controller instance reuse
- Default temperature: 0.7
- Max tokens: Determined by OpenAI (no artificial limit)

## Troubleshooting

### Common Issues

1. **"OpenAI API key is not configured"**
   - Set `OPENAI_API_KEY` in your `.env` file
   - Restart the application

2. **"Authentication failed"**
   - Verify your OpenAI API key is valid
   - Check if your organization ID is correct

3. **401 Unauthorized on endpoint**
   - Use valid client credentials as Bearer token
   - Format: `Authorization: Bearer client_id:client_secret`

4. **422 Validation Error**
   - Check that all required fields are provided
   - Ensure prompt and model are not empty

### Debug Mode

Enable debug logging to see detailed request information:

```python
import logging
logging.getLogger("controller.api_openai").setLevel(logging.DEBUG)
```