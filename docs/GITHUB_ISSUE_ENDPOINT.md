# GitHub Issue Creation Endpoint

## Overview

The GitHub Issue Creation endpoint allows you to automatically create well-formatted GitHub issues with AI-improved content. The endpoint processes raw text, improves it for clarity and structure, generates appropriate titles and categorizes the issue type automatically.

## Endpoint

**POST** `/api/github/create-issue`

## Features

- **Text Improvement**: AI enhances spelling, grammar and formatting
- **Smart Categorization**: Automatically determines if the issue is a bug, feature request, or task
- **Title Generation**: Creates concise, descriptive titles (max 80 characters)
- **Label Assignment**: Suggests relevant labels based on content
- **GitHub Integration**: Directly creates issues via GitHub API

## Request Format

```json
{
  "repository": "owner/repo",
  "text": "Raw issue description text..."
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repository` | string | Yes | GitHub repository in format "owner/repo" |
| `text` | string | Yes | Raw issue description text to be processed |

## Response Format

### Success Response (201 Created)

```json
{
  "issue_number": 42,
  "title": "Fix login validation bug",
  "issue_url": "https://github.com/owner/repo/issues/42",
  "success": true,
  "error_message": null
}
```

### Error Response (400/500)

```json
{
  "issue_number": 0,
  "title": "",
  "issue_url": "",
  "success": false,
  "error_message": "Error description"
}
```

## Authentication

This endpoint requires Bearer token authentication. Include your API key in the Authorization header:

```
Authorization: Bearer your_api_token
```

## Configuration Required

### 1. Environment Variables

Add the following to your `.env` file:

```env
# GitHub API Configuration
GITHUB_TOKEN=your_github_personal_access_token

# AI Provider (OpenAI by default)
OPENAI_API_KEY=your_openai_api_key
```

### 2. GitHub Setup

#### Step 1: Create a Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name like "UIS-KIGate-Integration"
4. Select the following scopes:
   - `repo` (Full control of private repositories)
   - `public_repo` (Access public repositories)
5. Click "Generate token"
6. **Important**: Copy the token immediately and store it securely

#### Step 2: Repository Permissions

Ensure the token has access to the repositories where you want to create issues:
- For personal repositories: The token owner must have write access
- For organization repositories: The token must belong to a user with write access to the repository

#### Step 3: Environment Configuration

Add your GitHub token to the `.env` file:

```env
GITHUB_TOKEN=ghp_your_generated_token_here
```

## Usage Examples

### Example 1: Bug Report

**Request:**
```bash
curl -X POST "https://your-domain.com/api/github/create-issue" \
  -H "Authorization: Bearer your_api_token" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "myorg/myapp",
    "text": "login button not work when click. error popup show but no message just empty box"
  }'
```

**Response:**
```json
{
  "issue_number": 15,
  "title": "Login button shows empty error popup on click",
  "issue_url": "https://github.com/myorg/myapp/issues/15",
  "success": true
}
```

### Example 2: Feature Request

**Request:**
```bash
curl -X POST "https://your-domain.com/api/github/create-issue" \
  -H "Authorization: Bearer your_api_token" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "myorg/myapp", 
    "text": "need dark mode theme option in settings for better user experience at night"
  }'
```

**Response:**
```json
{
  "issue_number": 16,
  "title": "Add dark mode theme option in settings",
  "issue_url": "https://github.com/myorg/myapp/issues/16",
  "success": true
}
```

## AI Processing Details

The endpoint uses AI to transform your input text through several steps:

1. **Text Improvement**: Corrects spelling, grammar, and improves clarity
2. **Structure Enhancement**: Organizes content with proper formatting (markdown)
3. **Title Generation**: Creates a concise, descriptive title
4. **Type Classification**: Determines if the issue is:
   - `bug` - Problem reports, errors, broken functionality
   - `enhancement` - Feature requests, improvements
   - `task` - General tasks, documentation, maintenance
5. **Label Suggestion**: Recommends relevant labels based on content

## Error Handling

### Common Errors

| Status Code | Error | Description | Solution |
|-------------|--------|-------------|----------|
| 400 | Invalid repository format | Repository format is not "owner/repo" | Check repository string format |
| 401 | Authentication failed | Invalid or missing API token | Verify Bearer token |
| 403 | GitHub API forbidden | Token lacks repository permissions | Check GitHub token permissions |
| 404 | Repository not found | Repository doesn't exist or token can't access it | Verify repository name and token access |
| 500 | AI processing failed | Text processing by AI failed | Try again or simplify input text |
| 500 | GitHub token not configured | GITHUB_TOKEN environment variable missing | Configure GitHub token |

### Example Error Response

```json
{
  "detail": "GitHub API error (404): Not Found"
}
```

## Security Considerations

1. **Token Security**: Keep your GitHub token secure and never expose it in client-side code
2. **Rate Limits**: GitHub API has rate limits (5000 requests/hour for authenticated requests)
3. **Repository Access**: Only provide tokens access to repositories where issue creation is intended
4. **Token Rotation**: Regularly rotate your GitHub tokens for security

## Troubleshooting

### Issue: "GitHub token not configured"
- Ensure `GITHUB_TOKEN` is set in your `.env` file
- Restart the application after adding the token

### Issue: "Repository not found" 
- Verify the repository exists and is accessible
- Check that your GitHub token has access to the repository
- Ensure repository format is exactly "owner/repo"

### Issue: "AI processing failed"
- Check that OpenAI API key is configured
- Verify the input text is not empty
- Try with simpler input text

### Issue: Rate limits exceeded
- GitHub API allows 5000 requests/hour for authenticated requests
- Implement appropriate delays between requests if processing many issues

## Testing

You can test the endpoint using the health check first:

```bash
curl -X GET "https://your-domain.com/health" \
  -H "Authorization: Bearer your_api_token"
```

If this works, your authentication is properly configured.