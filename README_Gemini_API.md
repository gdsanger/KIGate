# Google Gemini API Controller Documentation

## Overview

The Google Gemini API controller encapsulates the Gemini API functionality and provides a standardized interface for making AI requests. It accepts `aiapirequest` objects and returns `aiapiresult` objects with comprehensive error handling.

## Configuration

### Environment Variables

Set the following environment variables in your `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Required Dependencies

The controller requires the `google-generativeai` package, which is included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## API Endpoint

### POST /api/gemini

Processes AI requests using Google Gemini models.

**Authentication**: Bearer token required (client_id:client_secret)

**Request Body**:
```json
{
  "job_id": "unique-job-identifier",
  "user_id": "user-identifier", 
  "model": "gemini-pro",
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

The controller supports various Gemini models:
- `gemini-pro` (default)
- `gemini-pro-vision` (for multimodal tasks)
- Other available Gemini models

If an invalid model is specified, the controller falls back to `gemini-pro`.

## Usage Examples

### Using curl

```bash
# First, get an API key from the admin panel or create a user
# Then use the client_id:client_secret as Bearer token

curl -X POST "http://localhost:8000/api/gemini" \
  -H "Authorization: Bearer your_client_id:your_client_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "user_id": "user-456", 
    "model": "gemini-pro",
    "message": "Hello, how are you today?"
  }'
```

### Using Python

```python
import httpx
import asyncio

async def call_gemini_api():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/gemini",
            json={
                "job_id": "job-123",
                "user_id": "user-456",
                "model": "gemini-pro",
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

asyncio.run(call_gemini_api())
```

### Using the Controller Directly

```python
from model.aiapirequest import aiapirequest
from controller.api_gemini import process_gemini_request
import asyncio

async def direct_usage():
    request = aiapirequest(
        job_id="job-123",
        user_id="user-456",
        model="gemini-pro",
        message="Hello, how are you today?"
    )
    
    result = await process_gemini_request(request)
    
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
- **Missing API Key**: Returns error when `GEMINI_API_KEY` is not configured
- **Invalid Configuration**: Returns error when API client initialization fails

### Validation Errors  
- **Empty Message**: Returns error when the message field is empty
- **Empty Model**: Returns error when the model field is empty

### API Errors
- **Rate Limiting**: Detects and reports quota/rate limit exceeded errors
- **Authentication**: Detects and reports permission/authentication errors  
- **General API Errors**: Catches and reports other Gemini API errors
- **Unexpected Errors**: Catches and reports any unexpected errors

### Example Error Responses

**Missing API Key**:
```json
{
  "job_id": "job-123",
  "user_id": "user-456", 
  "content": "",
  "success": false,
  "error_message": "Gemini API key is not configured"
}
```

**Empty Message**:
```json
{
  "job_id": "job-123",
  "user_id": "user-456",
  "content": "",
  "success": false, 
  "error_message": "Validation error: Message cannot be empty"
}
```

**Rate Limit Error**:
```json
{
  "job_id": "job-123",
  "user_id": "user-456",
  "content": "",
  "success": false,
  "error_message": "Rate limit or quota exceeded: ..."
}
```

## Logging

The controller provides detailed logging at different levels:

- **INFO**: Successful operations, request processing
- **WARNING**: Fallback scenarios (e.g., model fallback to gemini-pro)  
- **ERROR**: Configuration issues, validation errors, API errors
- **DEBUG**: Detailed request information

## Testing

Run the Gemini controller tests:

```bash
python -m pytest test_gemini_controller.py -v
```

Or run the standalone test script:

```bash
python test_gemini_controller.py
```

## Security Considerations

1. **API Key Security**: Never expose your `GEMINI_API_KEY` in code or logs
2. **Authentication**: All endpoints require proper Bearer token authentication
3. **Input Validation**: All inputs are validated before processing
4. **Error Information**: Error messages don't expose sensitive configuration details

## Comparison with OpenAI Controller

| Feature | Gemini Controller | OpenAI Controller |
|---------|------------------|------------------|
| Input Field | `message` | `prompt` + `role` |
| Default Model | `gemini-pro` | No default |
| Model Fallback | Yes (to gemini-pro) | No |
| API Library | `google-generativeai` | `openai` |
| Authentication | API Key | API Key + Optional Org ID |

## Troubleshooting

### Common Issues

1. **"Gemini API key is not configured"**
   - Ensure `GEMINI_API_KEY` is set in your `.env` file
   - Verify the `.env` file is in the correct directory

2. **"Model not found" or model fallback warnings**
   - Check the model name is correct
   - Refer to Google's documentation for available models

3. **Authentication errors**
   - Verify your API key is valid and active
   - Check if your account has proper permissions

4. **Rate limit errors**  
   - Implement retry logic with exponential backoff
   - Check your API quota and usage limits

### Getting Help

For issues specific to the KIGate implementation, check the logs for detailed error information. For Google Gemini API issues, refer to the [official documentation](https://ai.google.dev/docs).