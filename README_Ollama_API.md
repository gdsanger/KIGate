# Ollama Integration

This document describes how to use Ollama local AI models with KIGate.

## Overview

Ollama support has been integrated into KIGate, allowing you to run local AI models on your infrastructure. This integration uses the Ollama API to communicate with your locally running Ollama instance.

## Prerequisites

1. Install Ollama on your local machine or server: https://ollama.ai
2. Start the Ollama service (usually runs on http://localhost:11434)
3. Pull a model: `ollama pull llama3.2` (or any other supported model)

## Configuration

### Using the Provider Entity (Database Configuration)

The recommended way to configure Ollama is through the Provider entity in the database:

1. Create a new provider with the following settings:
   - `name`: "Ollama Local" (or any descriptive name)
   - `provider_type`: "ollama"
   - `api_url`: "http://localhost:11434" (or your Ollama server URL)
   - `is_active`: true

2. Optionally, add models using the ProviderModel entity to manage which Ollama models are available

### Supported Provider Names

The following provider name variations are automatically recognized and normalized to "ollama":

- `ollama`
- `Ollama`
- `OLLAMA`
- `ollama (local)`
- `Ollama (local)`
- `Ollama (Local)`
- `ollama (loakl)` (handles common typo)

## Usage Example

```python
from service.ai_service import send_ai_request
from model.aiapirequest import aiapirequest

# Create a request
request = aiapirequest(
    job_id="unique-job-id",
    user_id="user-id",
    model="llama3.2",  # The Ollama model you want to use
    message="Hello, how are you?"
)

# Send the request
result = await send_ai_request(request, "ollama", db=db_session)

if result.success:
    print(f"Response: {result.content}")
else:
    print(f"Error: {result.error_message}")
```

## Available Models

You can fetch available models from your Ollama instance using the ProviderService:

```python
from service.provider_service import ProviderService

# Assuming you have a provider entity with id "provider-id"
models = await ProviderService.fetch_models_from_api(db, "provider-id")

for model in models:
    print(f"Model: {model.model_name} (ID: {model.model_id})")
```

## Troubleshooting

### Error: "Ollama API URL is not configured"

This error occurs when:
- No Ollama provider is configured in the database
- The provider is not active (`is_active = false`)
- The `api_url` field is not set

**Solution**: Create a Provider entity with `provider_type = "ollama"` and set the `api_url` to your Ollama server URL.

### Connection Errors

If you get connection errors, verify that:
1. Ollama is running: `curl http://localhost:11434/api/tags`
2. The URL in your provider configuration is correct
3. There are no firewall rules blocking the connection

### Model Not Found

If you get a "model not found" error:
1. List available models: `ollama list`
2. Pull the model: `ollama pull <model-name>`
3. Use the exact model name from `ollama list` in your request

## Implementation Details

- **Controller**: `controller/api_ollama.py` - Handles communication with Ollama API
- **Integration**: `service/ai_service.py` - Routes requests to the Ollama controller
- **Provider Model**: `model/provider.py` - Database entity for Ollama configuration
- **Tests**: `test_ollama_controller.py` and `test_ollama_integration.py`

## Dependencies

The Ollama integration requires the `ollama` Python package, which is included in `requirements.txt`.
