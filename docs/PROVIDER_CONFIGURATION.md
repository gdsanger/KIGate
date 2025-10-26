# Provider Configuration Guide

## Overview

The KIGate system now supports configurable AI providers with dynamic model management. This allows administrators to:

1. Configure multiple AI providers (OpenAI, Google Gemini, Claude, Ollama)
2. Fetch and manage available models from each provider
3. Select providers and models through dropdowns when creating/editing agents

## Supported Providers

### OpenAI
- **Required Configuration**: API Key
- **Optional Configuration**: Organization ID
- **Model Fetching**: Automatic via OpenAI API

### Google Gemini
- **Required Configuration**: API Key
- **Model Fetching**: Automatic via Google Generative AI API

### Claude (Anthropic)
- **Required Configuration**: API Key
- **Model Fetching**: Pre-configured list of available models

### Ollama
- **Required Configuration**: API URL (e.g., http://localhost:11434)
- **Model Fetching**: Automatic via Ollama API

## Configuration Steps

### 1. Add a Provider

1. Navigate to Admin Panel → Provider Verwaltung
2. Click "Neuen Provider erstellen"
3. Fill in the form:
   - **Name**: A descriptive name for the provider
   - **Provider-Typ**: Select from OpenAI, Google Gemini, Claude, or Ollama
   - **API Key**: Enter your API key (for OpenAI, Gemini, Claude)
   - **API URL**: Enter the API endpoint URL (for Ollama)
   - **Organization ID**: Optional for OpenAI
   - **Aktiv**: Check to enable the provider
4. Click "Erstellen"

### 2. Fetch Models

After creating a provider:

1. Click the cloud download icon next to the provider
2. Confirm the model fetch operation
3. The system will connect to the provider's API and retrieve available models
4. Models are automatically saved and activated

### 3. Manage Models

To activate or deactivate specific models:

1. Click the list icon next to the provider
2. A modal will show all available models
3. Click the play/pause icon to toggle model activation
4. Only active models will be available when creating agents

### 4. Create/Edit Agents

When creating or editing an agent:

1. The Provider dropdown will show all active providers
2. Select a provider
3. The Model dropdown will automatically populate with active models for that provider
4. Select the desired model
5. Complete the rest of the agent configuration

## Database Schema

### Provider Table
- `id`: Unique identifier
- `name`: Provider name
- `provider_type`: Type (openai, gemini, claude, ollama)
- `api_key`: API authentication key
- `api_url`: API endpoint URL (for Ollama)
- `organization_id`: Organization identifier (for OpenAI)
- `is_active`: Whether the provider is active
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### ProviderModel Table
- `id`: Unique identifier
- `provider_id`: Foreign key to Provider
- `model_name`: Display name of the model
- `model_id`: API identifier for the model
- `is_active`: Whether the model is active
- `created_at`: Creation timestamp

## API Endpoints

### Provider Management
- `GET /admin/providers` - Provider management page
- `POST /admin/providers/create` - Create a new provider
- `GET /admin/api/providers/{provider_id}` - Get provider details
- `POST /admin/providers/{provider_id}/update` - Update provider
- `DELETE /admin/providers/{provider_id}` - Delete provider

### Model Management
- `POST /admin/providers/{provider_id}/fetch-models` - Fetch models from provider API
- `POST /admin/providers/{provider_id}/models/{model_id}/toggle` - Toggle model activation
- `GET /admin/api/providers/{provider_id}/models` - Get active models for provider

### Agent Integration
- `GET /admin/api/providers-for-agents` - Get active providers for dropdown
- `GET /admin/api/providers/{provider_id}/models` - Get active models for dropdown

## Migration

The provider configuration feature is designed to work with existing installations:

1. On first run, SQLAlchemy will automatically create the `providers` and `provider_models` tables
2. Existing agents with hardcoded provider/model values will continue to work
3. Administrators can gradually migrate to the new provider configuration system
4. Agent YAML files will be updated to use the new provider names and model IDs

## Best Practices

1. **Security**: Store API keys securely and never commit them to version control
2. **Model Management**: Regularly update available models by re-fetching from providers
3. **Provider Naming**: Use descriptive names that indicate the provider type and purpose
4. **Testing**: Test agent functionality after adding new providers or models
5. **Cleanup**: Deactivate or delete unused providers to keep the system organized

## Troubleshooting

### Models Not Loading
- Verify the API key is correct
- Check network connectivity to the provider's API
- Ensure the provider is marked as active
- Check logs for specific error messages

### Agent Creation Fails
- Ensure at least one provider is active
- Verify the selected model is active
- Check that the provider has available models

### API Authentication Errors
- Verify API keys are current and valid
- For OpenAI, check if organization ID is required
- For Ollama, ensure the API URL is accessible
