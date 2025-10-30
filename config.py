from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_ORG_ID  = os.getenv("OPENAI_ORG_ID", "")

# Claude API
ANTHROPIC_API_KEY= os.getenv("ANTHROPIC_API_KEY", "")

# Google Gemmini API
GEMINI_API_KEY= os.getenv("GEMINI_API_KEY", "")

# ISARtec API / Ollama


# GitHub API
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_URL = "https://api.github.com"

# GraphAPI
ClientID = os.getenv("ClientId", "")
TenantID = os.getenv("TenantId", "")
ClientSecret = os.getenv("ClientSecret", "")
BaseUrl = os.getenv("BaseUrl", "")
Sender = "uis@isartec.de"

# Redis Cache Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() in ("true", "1", "yes")
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "21600"))  # 6 hours in seconds
CACHE_ERROR_TTL = int(os.getenv("CACHE_ERROR_TTL", "60"))  # 60 seconds for errors
