# Image Agent Execution Endpoint

## Overview

The Image Agent Execution Endpoint allows you to execute vision agents with image files as input for OCR text extraction. This endpoint is specifically designed for extracting text from images of receipts, invoices, payment confirmations, and other documents using Ollama's vision models (e.g., qwen3-vl:8b).

The endpoint accepts an image file, converts it to base64, sends it to the vision model, and returns the extracted text without any interpretation or structuring.

## Endpoint

```
POST /agent/execute-image
```

## Authentication

Requires Bearer token authentication (same as other agent endpoints).

## Request Format

The request uses `multipart/form-data` format:

- `request` (string, required): JSON string containing the agent execution parameters  
- `image_file` (file, required): Image file to process (PNG, JPEG, or WEBP)

### JSON Structure in `request` field

```json
{
  "agent_name": "image-ocr-extractor-de",
  "provider": "Ollama",
  "model": "qwen3-vl:8b",
  "user_id": "string",
  "parameters": {
    "additionalProp1": "value1"
  }
}
```

### Field Descriptions

- `agent_name` (string, required): Name of the vision agent to execute (e.g., "image-ocr-extractor-de")
- `provider` (string, optional): AI provider - will be overridden by agent configuration (must be "Ollama" for vision models)
- `model` (string, optional): AI model - will be overridden by agent configuration (e.g., "qwen3-vl:8b")
- `user_id` (string, required): User ID for tracking and rate limiting
- `parameters` (object, optional): Optional key-value parameters for the agent

**Note:** The provider and model fields are optional in the request. The endpoint will always use the provider and model configured in the agent's YAML file to ensure compatibility with vision models.

### Image File Requirements

- **Supported formats**: PNG (.png), JPEG (.jpg, .jpeg), WEBP (.webp)
- **Maximum size**: 10 MB
- **Content types**: `image/png`, `image/jpeg`, `image/webp`

## Response

```json
{
  "success": true,
  "text": "Extracted text from the image...",
  "agent": "image-ocr-extractor-de",
  "provider": "Ollama",
  "model": "qwen3-vl:8b",
  "job_id": "uuid-string",
  "image_filename": "invoice.png"
}
```

### Response Fields

- `success` (boolean): Indicates whether the text extraction was successful
- `text` (string): The extracted text from the image (or error message if failed)
- `agent` (string): Name of the agent that processed the image
- `provider` (string): AI provider used (from agent configuration)
- `model` (string): AI model used (from agent configuration)
- `job_id` (string): Job ID for tracking the request
- `image_filename` (string): Original filename of the uploaded image

## Example Usage

### Using curl

```bash
curl -X POST "http://localhost:8000/agent/execute-image" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F 'request={"agent_name":"image-ocr-extractor-de","user_id":"user-123"}' \
  -F "image_file=@/path/to/invoice.png"
```

### Using Python

```python
import requests

url = "http://localhost:8000/agent/execute-image"
headers = {
    "Authorization": "Bearer YOUR_TOKEN_HERE"
}

# Prepare the request data
request_data = {
    "agent_name": "image-ocr-extractor-de",
    "user_id": "user-123"
}

# Prepare the files
files = {
    'request': (None, json.dumps(request_data), 'application/json'),
    'image_file': ('invoice.png', open('/path/to/invoice.png', 'rb'), 'image/png')
}

# Send the request
response = requests.post(url, headers=headers, files=files)
result = response.json()

if result['success']:
    print("Extracted text:")
    print(result['text'])
else:
    print("Error:", result['text'])
```

### Using JavaScript (fetch)

```javascript
const formData = new FormData();

// Add request JSON
const requestData = {
  agent_name: "image-ocr-extractor-de",
  user_id: "user-123"
};
formData.append('request', JSON.stringify(requestData));

// Add image file
const imageFile = document.getElementById('fileInput').files[0];
formData.append('image_file', imageFile);

// Send request
fetch('http://localhost:8000/agent/execute-image', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN_HERE'
  },
  body: formData
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log('Extracted text:', data.text);
  } else {
    console.error('Error:', data.text);
  }
});
```

## Error Handling

The endpoint returns appropriate HTTP status codes and error messages:

- **400 Bad Request**: Invalid JSON, unsupported image format, image too large, or validation errors
- **404 Not Found**: Agent not found
- **500 Internal Server Error**: Unexpected server error

Example error response:
```json
{
  "detail": "Unsupported image format. Supported formats: png, jpeg, webp"
}
```

## Use Case: Integration with Finoa

This endpoint is designed to work with the Finoa pipeline:

1. **Finoa** sends an image file (receipt, invoice, payment confirmation) to KIGate
2. **KIGate** processes the image through the `image-ocr-extractor-de` agent using `qwen3-vl:8b`
3. **KIGate** returns raw OCR text
4. **Finoa** sends this text to the existing Gemma agent for structured data extraction

This two-step process separates OCR extraction from data structuring, providing flexibility and better results.

## Agent Configuration

The default agent `image-ocr-extractor-de` is configured in `/agents/image-ocr-extractor-de.yml`:

```yaml
name: image-ocr-extractor-de
provider: Ollama
model: qwen3-vl:8b
description: Vision-Agent for extracting text from receipts and invoices
```

The agent is optimized for German-language documents and focuses on:
- Invoice numbers and receipt numbers
- Amounts, dates, and times
- Sender names and company information
- Tax/VAT details (Brutto/Netto)
- All recognizable text elements

## Notes

- The endpoint uses Ollama's vision model API with base64-encoded images
- No chunking is performed (unlike PDF/DOCX endpoints) since images are processed as a single unit
- The extracted text is returned as-is, without JSON structuring or interpretation
- Job tracking and rate limiting are automatically applied
- The vision model must be available in your Ollama installation (`ollama pull qwen3-vl:8b`)

## Related Endpoints

- `/agent/execute` - Execute agents with text messages
- `/agent/execute-pdf` - Execute agents with PDF files
- `/agent/execute-docx` - Execute agents with DOCX files
