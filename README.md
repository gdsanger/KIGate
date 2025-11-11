# KIGate API - SQLite Database & Admin Panel

Centralized agent-driven API Gateway for AI with integrated user management system.

## Features

- 🗄️ **SQLite Database** - Async SQLite with SQLAlchemy
- 🎛️ **Admin Panel** - Modern Bootstrap-based web interface  
- 👥 **User Management** - Complete CRUD operations
- 🤖 **Agent Management** - YAML-based AI agent configuration and management
- 🔌 **Provider Configuration** - Dynamic AI provider and model management (OpenAI, Gemini, Claude, Ollama)
- 📊 **Job Statistics** - Comprehensive usage analytics with charts and cost tracking
- 🛡️ **Authentication** - Bearer token and API key authentication
- 🔒 **Security** - 128-bit client secrets, user activation/deactivation

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

**Important:** All dependencies in `requirements.txt` must be installed before starting the application. This includes packages for all AI providers (OpenAI, Claude, Gemini, Ollama) even if you don't plan to use all of them immediately.

2. Start the application:
```bash
uvicorn main:app --reload
```

3. Access the admin panel: http://localhost:8000/admin

## Usage

### Admin Panel

- **Dashboard**: http://localhost:8000/admin
- **User Management**: http://localhost:8000/admin/users
- **Agent Management**: http://localhost:8000/admin/agents
- **Provider Configuration**: http://localhost:8000/admin/providers
- **Job Statistics**: http://localhost:8000/admin/job-statistics
- **API Documentation**: http://localhost:8000/docs

For detailed information on provider configuration, see [Provider Configuration Guide](docs/PROVIDER_CONFIGURATION.md).

### API Authentication

**Bearer Token** (recommended for applications):
```bash
curl -H "Authorization: Bearer {client_id}:{client_secret}" http://localhost:8000/secure-endpoint
```

**Query Parameter** (for simple requests):
```bash
curl "http://localhost:8000/health?api_key={client_id}:{client_secret}"
```

### User Management Features

- ✅ Create new users with automatic GUID generation
- ✅ Edit user information (name, email, status)
- ✅ Generate new 128-bit client secrets
- ✅ Activate/deactivate users
- ✅ Delete users with confirmation
- ✅ Track last login timestamps

### Agent Management Features

- ✅ Create and configure AI agents via web interface
- ✅ YAML-based agent configuration with validation
- ✅ Support for multiple AI providers (OpenAI, Claude, etc.)
- ✅ Parameter definition for flexible agent behavior
- ✅ Agent cloning and versioning
- ✅ Real-time agent testing and validation

📖 **[Complete Agent Documentation](README_AGENTS.md)** - Learn how to create and manage AI agents  
🚀 **[Quick Start Guide](QUICK_START_AGENTS.md)** - Get started with agents in 5 minutes

### Job Statistics Features

- ✅ Multi-dimensional analytics (by agent, provider, model)
- ✅ Time-based aggregation (daily, weekly, monthly)
- ✅ Interactive charts and visualizations with Chart.js
- ✅ Cost tracking with automatic calculation from token usage
- ✅ Manual refresh from UI
- ✅ Automated updates via CLI script for cron jobs
- ✅ Performance metrics including average job duration

📊 **[Job Statistics Documentation](JOB_STATISTICS_DOCUMENTATION.md)** - Complete guide to usage analytics and cost tracking

### Automated Statistics Updates

To set up daily automated statistics updates via cron:

```bash
# Run daily at 1:00 AM
0 1 * * * cd /path/to/KIGate && /usr/bin/python3 cli_update_statistics.py >> /var/log/kigate_stats.log 2>&1
```

## Database Schema

The `users` table includes:
- `client_id`: Unique GUID (Primary Key)
- `client_secret`: 128-bit hex string for authentication
- `name`: User display name (required)
- `email`: Optional email address
- `is_active`: Boolean for user activation status
- `created_at`: User creation timestamp
- `last_login`: Last authentication timestamp

## Security Notes

- Client secrets are 128-bit secure random hex strings
- Database file (`kigate.db`) is excluded from version control
- User authentication updates last login timestamp automatically
- Inactive users cannot authenticate even with valid credentials

## API Documentation

📚 **Comprehensive API Documentation**: [`API_Documentation.md`](API_Documentation.md)  
📖 **Wiki-Ready Version**: [`docs/API_Wiki_Documentation.md`](docs/API_Wiki_Documentation.md)  
⚡ **Quick Reference**: [`docs/API_Quick_Reference.md`](docs/API_Quick_Reference.md)

The documentation covers:
- `/agent/execute` endpoint usage
- Authentication methods
- Provider system (OpenAI, Claude, Gemini, ISARtec)
- Available models and agents
- Implementation examples
- Error handling

**Contact for API access**: Christian Angermeier (christian.angermeier@isartec.de)

## Development

Run tests:
```bash
python test_implementation.py
python test_database_migration.py  # Test database migration functionality
```

The test suite validates:
- Database operations
- API authentication
- Admin panel functionality
- User management features
- Database schema migrations

### Database Migration

The application includes automatic database migration to handle schema updates. When starting the application, it will automatically detect and add any missing columns (such as the `duration` column in the jobs table) to ensure compatibility with existing databases.