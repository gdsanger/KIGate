# Rate Limiting Documentation

## Overview

KIGate now supports user-level rate limiting with two types of limits:
- **RPM (Requests Per Minute)**: Limits the number of API requests a user can make per minute
- **TPM (Tokens Per Minute)**: Limits the number of AI tokens consumed per minute

## Default Limits

- **Default RPM**: 20 requests per minute
- **Default TPM**: 50,000 tokens per minute

## How It Works

### 1. User Rate Limit Fields

Each user has the following rate limit fields in the database:

| Field | Type | Description |
|-------|------|-------------|
| `rpm_limit` | Integer | Maximum requests allowed per minute (default: 20) |
| `tpm_limit` | Integer | Maximum tokens allowed per minute (default: 50000) |
| `current_rpm` | Integer | Current request count in the current minute |
| `current_tpm` | Integer | Current token count in the current minute |
| `last_reset_time` | DateTime | Timestamp of the last counter reset |

### 2. Rate Limit Enforcement

Rate limits are enforced at two stages:

**During Authentication:**
- Every API request first checks the user's RPM limit
- If the user has exceeded their RPM limit, a `429 Too Many Requests` error is returned
- If within limits, the request counter is incremented

**After AI Processing:**
- Token usage from AI providers (OpenAI, Gemini, Claude) is tracked
- Token count is added to the user's `current_tpm`
- Future requests check if adding estimated tokens would exceed the TPM limit

### 3. Rate Limit Reset

- Counters automatically reset after 60 seconds
- When `last_reset_time` is more than 60 seconds old, both `current_rpm` and `current_tpm` are reset to 0

## HTTP Error Codes

When rate limits are exceeded, the API returns:

**Status Code:** `429 Too Many Requests`

**Response Body:**
```json
{
  "detail": "Rate limit exceeded: 20/20 requests per minute"
}
```

**Headers:**
```
Retry-After: 60
```

## API Endpoints with Rate Limiting

All authenticated endpoints enforce rate limits:

- `/api/openai` - OpenAI API endpoint
- `/api/gemini` - Google Gemini API endpoint  
- `/api/claude` - Anthropic Claude API endpoint
- `/agent/execute` - Agent execution endpoint
- `/agent/execute-pdf` - PDF agent execution endpoint
- `/agent/execute-docx` - DOCX agent execution endpoint

## Managing User Rate Limits

### Creating Users with Custom Limits

When creating a user via the admin API, you can specify custom rate limits:

```bash
curl -X POST "http://localhost:8000/admin/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom User",
    "email": "custom@example.com",
    "rpm_limit": 100,
    "tpm_limit": 200000
  }'
```

### Updating User Rate Limits

Update existing user limits via the admin API:

```bash
curl -X PUT "http://localhost:8000/admin/users/{client_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "rpm_limit": 50,
    "tpm_limit": 100000
  }'
```

### Viewing User Rate Limit Status

When retrieving user information, rate limit fields are included in the response:

```json
{
  "client_id": "abc-123-def",
  "name": "Test User",
  "email": "test@example.com",
  "is_active": true,
  "rpm_limit": 20,
  "tpm_limit": 50000,
  "current_rpm": 5,
  "current_tpm": 1250,
  "last_reset_time": "2025-10-26T18:30:00Z"
}
```

## Token Estimation

For endpoints where exact token usage isn't available, the system uses estimation:
- **Estimation Formula**: ~1 token per 4 characters
- Used for rate limit checks before processing

## Testing Rate Limits

### Automated Tests

Run the rate limiting tests:

```bash
pytest test_rate_limiting.py -v
pytest test_rate_limiting_integration.py -v
```

### Manual Testing

1. Create a test user with low limits:
```bash
python test_manual_rate_limiting.py
```

2. Make requests using the provided credentials:
```bash
curl -X GET http://localhost:8000/secure-endpoint \
  -H 'Authorization: Bearer {client_id}:{client_secret}'
```

3. After reaching the limit (3 requests), you'll receive a 429 error

4. Wait 60 seconds and try again - the limit will reset

## Implementation Details

### Rate Limit Service

The `RateLimitService` class in `service/rate_limit_service.py` handles:
- Checking rate limits before processing
- Recording request and token usage
- Token estimation

### User Model Methods

The `User` model includes helper methods:
- `reset_rate_limits_if_needed()` - Resets counters if > 60 seconds have passed
- `check_rpm_limit()` - Returns True if within RPM limit
- `check_tpm_limit(tokens)` - Returns True if adding tokens won't exceed limit
- `increment_request_count()` - Increments RPM counter
- `add_token_usage(tokens)` - Adds tokens to TPM counter

### Database Migration

Database migrations automatically add rate limit columns to existing databases:
- `rpm_limit` (default: 20)
- `tpm_limit` (default: 50000)
- `current_rpm` (default: 0)
- `current_tpm` (default: 0)
- `last_reset_time` (nullable)

## Performance Considerations

- Rate limit checks add minimal overhead (~1-2ms per request)
- Counters are stored in the database and updated per request
- Reset checks are lightweight (simple timestamp comparison)
- Token tracking from AI providers uses native response data when available

## Best Practices

1. **Set appropriate limits** based on user tiers or plans
2. **Monitor usage** through the user API to identify patterns
3. **Adjust limits** proactively for users approaching their limits
4. **Communicate limits** to API consumers in documentation
5. **Use the Retry-After header** to implement exponential backoff in clients
