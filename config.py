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
