from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Form, Request
from fastapi.openapi.utils import get_openapi
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
import yaml
import time
import logging
from datetime import datetime, timezone

from database import init_db, close_db, get_async_session
from admin_routes import admin_router
from auth import authenticate_user_by_token, get_current_user_by_api_key
from model.user import User
from model.aiapirequest import aiapirequest
from model.aiapiresult import aiapiresult
from model.agent_execution import AgentExecutionRequest, AgentExecutionResponse
from model.pdf_agent_execution import PDFAgentExecutionRequest, PDFAgentExecutionResponse
from model.docx_agent_execution import DocxAgentExecutionRequest, DocxAgentExecutionResponse
from model.job import JobCreate
from model.github_issue import GitHubIssueRequest, GitHubIssueResponse
from model.ai_audit_log import AIAuditLogCreate
from service.agent_service import AgentService
from service.job_service import JobService
from service.ai_service import send_ai_request
from service.github_service import GitHubService
from service.github_issue_processor import GitHubIssueProcessor
from service.pdf_service import PDFService
from service.docx_service import DocxService
from service.settings_service import SettingsService
from service.ai_audit_log_service import AIAuditLogService
from service.cache_service import CacheService
from controller.api_openai import process_openai_request
from controller.api_gemini import process_gemini_request
from controller.api_claude import process_claude_request
from logging_config import LoggingConfig
from utils.request_utils import get_client_ip, extract_auth_token
from utils.token_counter import count_tokens
from pydantic import ValidationError
import config

# Initialize logging system
LoggingConfig.setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting KIGate API...")
    
    # Check dependencies before initializing
    from utils.dependency_checker import DependencyChecker
    all_core_installed, missing_providers = DependencyChecker.verify_all_dependencies()
    
    if not all_core_installed:
        logger.error("Cannot start application - core dependencies are missing!")
        logger.error("Please run: pip install -r requirements.txt")
        raise RuntimeError("Core dependencies missing. Please run: pip install -r requirements.txt")
    
    await init_db()
    
    # Initialize Redis cache
    CacheService.initialize()
    
    # Initialize default settings and load Sentry configuration
    async for db in get_async_session():
        await SettingsService.initialize_default_settings(db)
        await db.commit()
        
        # Load Sentry settings and initialize if configured
        sentry_dsn = await SettingsService.get_setting_value(db, "sentry_dsn")
        if sentry_dsn:
            sentry_env = await SettingsService.get_setting_value(db, "sentry_environment", "production")
            sentry_rate_str = await SettingsService.get_setting_value(db, "sentry_traces_sample_rate", "0.1")
            try:
                sentry_rate = float(sentry_rate_str)
            except (ValueError, TypeError):
                sentry_rate = 0.1
            
            LoggingConfig.setup_sentry(dsn=sentry_dsn, environment=sentry_env, 
                                      traces_sample_rate=sentry_rate)
        
        break
    
    logger.info("KIGate API started successfully")
    yield
    # Shutdown
    logger.info("Shutting down KIGate API...")
    await close_db()
    logger.info("KIGate API shutdown complete")


app = FastAPI(lifespan=lifespan)

# Middleware for audit logging
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """Middleware to log all API calls to audit log"""
    # Only log API endpoints (not admin, static, health, etc.)
    if request.url.path.startswith("/api/"):
        # Extract request information
        client_ip = get_client_ip(request)
        api_endpoint = request.url.path
        auth_token = extract_auth_token(request)
        
        # For audit logging, we'll capture basic info without reading body
        # Body reading in middleware causes issues with FastAPI request parsing
        payload_preview = f"Method: {request.method}, Path: {request.url.path}"
        
        # Call the endpoint first
        response = await call_next(request)
        
        # Log to audit log asynchronously after response
        try:
            async for db in get_async_session():
                # Mask the token for security
                masked_token = AIAuditLogService.mask_secret(auth_token) if auth_token else None
                
                audit_log_data = AIAuditLogCreate(
                    client_ip=client_ip,
                    api_endpoint=api_endpoint,
                    client_secret=masked_token,
                    payload_preview=payload_preview,
                    status_code=response.status_code
                )
                
                await AIAuditLogService.create_log(db, audit_log_data)
                await db.commit()
                break
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
        
        return response
    else:
        # For non-API endpoints, just pass through
        return await call_next(request)
# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

def custom_api():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="KiGate API",
        version="1.0.0",
        description="centralized agent-driven API Gateway for AI",
        routes=app.routes,
    )

    openapi_schema["servers"] = [
        {
            "url": "https://kigate.isarlabs.de",
            "description": "Produktivserver"
        },
        {
            "url": "http://localhost:8000",
            "description": "Lokaler Entwicklungsserver"
        }
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_api

# Include admin routes
app.include_router(admin_router)

@app.get("/health")
async def health(api_key: Optional[str] = Query(None, description="API Key in format client_id:client_secret")):
    """Health check endpoint with optional authentication"""
    response = {"status": "ok"}
    
    if api_key:
        from database import get_async_session
        from service.user_service import UserService
        
        # Manual authentication for this endpoint
        try:
            if ':' in api_key:
                client_id, client_secret = api_key.split(':', 1)
                async for db in get_async_session():
                    user = await UserService.authenticate_user(db, client_id, client_secret)
                    if user:
                        await db.commit()
                        response["authenticated_user"] = user.name
                        response["client_id"] = user.client_id
                    else:
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    break
            else:
                raise HTTPException(status_code=401, detail="Invalid API key format")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid API key format")
    
    return response


@app.get("/secure-endpoint")
async def secure_endpoint(current_user: User = Depends(authenticate_user_by_token)):
    """Example of a secured endpoint requiring Bearer token authentication"""
    return {
        "message": "This is a secured endpoint",
        "user": current_user.name,
        "client_id": current_user.client_id
    }


@app.get("/api/agents")
async def get_agents(api_key: Optional[str] = Query(None, description="API Key in format client_id:client_secret")):
    """Get all agents with their details in JSON format"""
    # Optional authentication - endpoint works without API key but can provide additional info if authenticated
    authenticated_user = None
    if api_key:
        from database import get_async_session
        from service.user_service import UserService
        
        try:
            if ':' in api_key:
                client_id, client_secret = api_key.split(':', 1)
                async for db in get_async_session():
                    user = await UserService.authenticate_user(db, client_id, client_secret)
                    if user:
                        await db.commit()
                        authenticated_user = user.name
                    break
        except (ValueError, Exception):
            # If authentication fails, just proceed without authentication
            pass
    
    # Get all agents
    agents = await AgentService.get_all_agents()
    
    # Convert to dict format for JSON response
    agents_data = []
    for agent in agents:
        agent_dict = agent.dict()
        agents_data.append(agent_dict)
    
    response = {
        "agents": agents_data,
        "count": len(agents_data)
    }
    
    if authenticated_user:
        response["authenticated_as"] = authenticated_user
    
    return response


@app.post("/api/openai", response_model=aiapiresult)
async def openai_endpoint(
    request: aiapirequest, 
    current_user: User = Depends(authenticate_user_by_token),
    db: AsyncSession = Depends(get_async_session)
):
    """
    OpenAI API endpoint that processes AI requests
    
    Accepts aiapirequest objects and returns aiapiresult objects.
    Requires authentication via Bearer token.
    Rate limited by RPM and TPM.
    """
    from service.rate_limit_service import RateLimitService
    
    try:
        # Process the request using the OpenAI controller
        result = await process_openai_request(request)
        
        # Record the request and token usage for rate limiting
        await RateLimitService.record_request(db, current_user, result.tokens_used)
        await db.commit()
        
        return result
    except Exception as e:
        # If there's an unexpected error in the endpoint itself
        return aiapiresult(
            job_id=request.job_id,
            user_id=request.user_id,
            content="",
            success=False,
            error_message=f"Endpoint error: {str(e)}"
        )

@app.post("/agent/execute", response_model=AgentExecutionResponse)
async def execute_agent(request: Request, agent_request: AgentExecutionRequest, current_user: User = Depends(authenticate_user_by_token)):
    """
    Execute an agent with the specified configuration
    
    This endpoint:
    1. Checks cache if enabled (cache-aside strategy)
    2. Loads the agent configuration from YAML file
    3. Creates a job in the database
    4. Combines agent role/task with user message
    5. Routes request to appropriate AI provider
    6. Caches the result for future requests
    7. Returns structured response with job details, result, and cache metadata
    Rate limited by RPM and TPM.
    """
    from service.rate_limit_service import RateLimitService
    from model.agent_execution import CacheMetadata
    
    try:
        # Extract client IP
        client_ip = get_client_ip(request)
        
        # Load agent configuration from YAML
        agent = await AgentService.get_agent_by_name(agent_request.agent_name)
        if not agent:
            raise HTTPException(
                status_code=404, 
                detail=f"Agent '{agent_request.agent_name}' not found"
            )
        
        # Note: User-provided provider and model are accepted but ignored.
        # Always use the provider and model from the agent configuration.
        
        # Check cache if enabled and not forcing refresh
        cache_metadata = None
        if agent_request.use_cache and not agent_request.force_refresh:
            cached_result = await CacheService.get_cached_result(
                agent_name=agent_request.agent_name,
                provider=agent.provider,
                model=agent.model,
                user_id=agent_request.user_id,
                message=agent_request.message,
                parameters=agent_request.parameters
            )
            
            if cached_result:
                result, metadata = cached_result
                
                # Extract required fields from cache metadata
                job_id = metadata.get("job_id")
                status = metadata.get("status")
                
                # Log warning if fallback values would be needed
                if not job_id:
                    logger.warning(f"Cache entry missing job_id, using fallback value")
                    job_id = "cached"
                if not status:
                    logger.warning(f"Cache entry missing status, using fallback value")
                    status = "completed"
                
                cache_metadata = CacheMetadata(
                    status="hit",
                    cached_at=metadata.get("cached_at"),
                    ttl=metadata.get("ttl")
                )
                
                return AgentExecutionResponse(
                    job_id=job_id,
                    agent=agent_request.agent_name,
                    provider=agent.provider,
                    model=agent.model,
                    status=status,
                    result=result,
                    cache=cache_metadata
                )
        
        # Determine cache status for response
        if not agent_request.use_cache:
            cache_status = "bypassed"
        else:
            cache_status = "miss"
        
        # Create job in database
        async for db in get_async_session():
            # Prepare AI request by combining agent configuration with user message
            # Apply parameters to the agent task if provided
            processed_task = agent.task
            if agent_request.parameters:
                # Process parameters into the task using efficient string joining
                param_lines = [f"{key}: {value}" for key, value in agent_request.parameters.items()]
                param_context = "\n".join(param_lines)
                processed_task = f"{agent.task}\n\nParameters:\n{param_context}"
            
            combined_message = f"{agent.role}\n\n{processed_task}\n\nUser message: {agent_request.message}"
            
            # Count tokens in the combined message using agent's model
            token_count = count_tokens(combined_message, agent.model)
            
            job_data = JobCreate(
                name=f"{agent_request.agent_name}-job",
                user_id=agent_request.user_id,
                provider=agent.provider,
                model=agent.model,
                status="created",
                client_ip=client_ip,
                token_count=token_count
            )
            
            job = await JobService.create_job(db, job_data)
            
            # Track start time for duration calculation
            start_time = time.time()
            
            ai_request = aiapirequest(
                job_id=job.id,
                user_id=agent_request.user_id,
                model=agent.model,
                message=combined_message
            )
            
            # Update job status to processing
            await JobService.update_job_status(db, job.id, "processing")
            await db.commit()
            
            try:
                # Send request to AI provider using agent's provider
                ai_result = await send_ai_request(ai_request, agent.provider, db)
                
                # Record the request and token usage for rate limiting
                await RateLimitService.record_request(db, current_user, ai_result.tokens_used)
                
                # Calculate duration in milliseconds
                duration_ms = int((time.time() - start_time) * 1000)
                
                if ai_result.success:
                    # Update job status to completed
                    await JobService.update_job_status(db, job.id, "completed")
                    await JobService.update_job_duration(db, job.id, duration_ms)
                    status = "completed"
                    result = ai_result.content
                else:
                    # Update job status to failed
                    await JobService.update_job_status(db, job.id, "failed")
                    await JobService.update_job_duration(db, job.id, duration_ms)
                    status = "failed"
                    result = ai_result.error_message or "AI processing failed"
                
                await db.commit()
                
                # Cache the result if caching is enabled
                if agent_request.use_cache:
                    await CacheService.set_cached_result(
                        agent_name=agent_request.agent_name,
                        provider=agent.provider,
                        model=agent.model,
                        user_id=agent_request.user_id,
                        message=agent_request.message,
                        result=result,
                        status=status,
                        job_id=job.id,
                        parameters=agent_request.parameters,
                        ttl=agent_request.cache_ttl
                    )
                    
                    # Create cache metadata for response
                    cache_metadata = CacheMetadata(
                        status=cache_status,
                        cached_at=datetime.now(timezone.utc).isoformat(),
                        ttl=agent_request.cache_ttl or (
                            config.CACHE_ERROR_TTL if status == "failed" else config.CACHE_DEFAULT_TTL
                        )
                    )
                else:
                    cache_metadata = CacheMetadata(
                        status=cache_status,
                        cached_at=None,
                        ttl=None
                    )
                
                return AgentExecutionResponse(
                    job_id=job.id,
                    agent=agent_request.agent_name,
                    provider=agent.provider,
                    model=agent.model,
                    status=status,
                    result=result,
                    cache=cache_metadata
                )
                
            except Exception as ai_error:
                # Calculate duration even on error
                duration_ms = int((time.time() - start_time) * 1000)
                # Update job status to failed
                await JobService.update_job_status(db, job.id, "failed")
                await JobService.update_job_duration(db, job.id, duration_ms)
                await db.commit()
                
                raise HTTPException(
                    status_code=500,
                    detail=f"AI processing error: {str(ai_error)}"
                )
            
            break  # Exit the async for loop
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )



@app.post("/api/gemini", response_model=aiapiresult)
async def gemini_endpoint(
    request: aiapirequest, 
    current_user: User = Depends(authenticate_user_by_token),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Google Gemini API endpoint that processes AI requests
    
    Accepts aiapirequest objects and returns aiapiresult objects.
    Requires authentication via Bearer token.
    Rate limited by RPM and TPM.
    """
    from service.rate_limit_service import RateLimitService
    
    try:
        # Process the request using the Gemini controller
        result = await process_gemini_request(request)
        
        # Record the request and token usage for rate limiting
        await RateLimitService.record_request(db, current_user, result.tokens_used)
        await db.commit()
        
        return result
    except Exception as e:
        # If there's an unexpected error in the endpoint itself
        return aiapiresult(
            job_id=request.job_id,
            user_id=request.user_id,
            content="",
            success=False,
            error_message=f"Endpoint error: {str(e)}"
        )
      
@app.post("/api/claude", response_model=aiapiresult)
async def claude_endpoint(
    request: aiapirequest, 
    current_user: User = Depends(authenticate_user_by_token),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Claude API endpoint that processes AI requests
    
    Accepts aiapirequest objects and returns aiapiresult objects.
    Requires authentication via Bearer token.
    Rate limited by RPM and TPM.
    """
    from service.rate_limit_service import RateLimitService
    
    try:
        # Process the request using the Claude controller
        result = await process_claude_request(request)
        
        # Record the request and token usage for rate limiting
        await RateLimitService.record_request(db, current_user, result.tokens_used)
        await db.commit()
        
        return result
    except Exception as e:
        # If there's an unexpected error in the endpoint itself
        return aiapiresult(
            job_id=request.job_id,
            user_id=request.user_id,
            content="",
            success=False,
            error_message=f"Endpoint error: {str(e)}"
        )


@app.post("/api/github/create-issue", response_model=GitHubIssueResponse)
async def create_github_issue(request: GitHubIssueRequest, current_user: User = Depends(authenticate_user_by_token)):
    """
    Create a GitHub issue with AI-improved content
    
    This endpoint:
    1. Validates the repository format
    2. Uses AI to improve the text for spelling, grammar and clarity
    3. Generates an appropriate issue title and type classification
    4. Creates the issue via GitHub API
    5. Returns the issue number and title
    
    Requires GitHub token configuration and authentication.
    """
    try:
        # Validate repository format
        if not GitHubService.validate_repository_format(request.repository):
            raise HTTPException(
                status_code=400,
                detail="Invalid repository format. Expected format: 'owner/repo'"
            )
        
        # Process text with AI
        processed_content = await GitHubIssueProcessor.process_issue_text(
            text=request.text,
            user_id=current_user.client_id,
            provider="openai",  # Default to OpenAI, could be configurable
            model="gpt-3.5-turbo"
        )
        
        if not processed_content:
            raise HTTPException(
                status_code=500,
                detail="Failed to process issue text with AI"
            )
        
        # Create GitHub issue
        result = await GitHubService.create_issue(request.repository, processed_content)
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create GitHub issue: {result.error_message}"
            )
        
        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/agent/execute-pdf", response_model=PDFAgentExecutionResponse)
async def execute_agent_pdf(
    http_request: Request,
    request: str = Form(...),
    pdf_file: UploadFile = File(...),
    current_user: User = Depends(authenticate_user_by_token)
):
    """
    Execute an agent with a PDF file instead of text message
    
    This endpoint:
    1. Parses JSON request data (similar to /agent/execute structure)
    2. Loads the agent configuration from YAML file
    3. Extracts text from the uploaded PDF file
    4. Splits large text into chunks if needed (respecting token limits)
    5. Processes each chunk through the agent
    6. Merges results from all chunks into a final response
    7. Returns structured response with job details and merged result
    
    Request format: multipart/form-data with:
    - request: JSON string containing agent_name, provider, model, user_id, parameters, chunk_size
    - pdf_file: PDF file to process
    """
    try:
        # Extract client IP
        client_ip = get_client_ip(http_request)
        
        # Parse JSON request data
        try:
            request_data = json.loads(request)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in request field: {str(e)}"
            )
        
        try:
            pdf_request = PDFAgentExecutionRequest(**request_data)
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request data: {str(e)}"
            )
        
        # Extract fields from parsed request
        agent_name = pdf_request.agent_name
        provider = pdf_request.provider
        model = pdf_request.model
        user_id = pdf_request.user_id
        parameters = pdf_request.parameters
        chunk_size = pdf_request.chunk_size or 4000
        
        # Validate PDF file
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="File must be a PDF (.pdf extension required)"
            )
        
        # Load agent configuration from YAML
        agent = await AgentService.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(
                status_code=404, 
                detail=f"Agent '{agent_name}' not found"
            )
        
        # Note: User-provided provider and model are accepted but ignored.
        # Always use the provider and model from the agent configuration.
        # Override with agent's configuration
        provider = agent.provider
        model = agent.model
        
        # Extract text from PDF
        pdf_text = await PDFService.extract_text_from_pdf(pdf_file)
        
        # Split text into chunks if needed
        text_chunks = PDFService.chunk_text(pdf_text, chunk_size=chunk_size)
        
        # Process each chunk
        chunk_results = []
        job_ids = []
        
        async for db in get_async_session():
            for i, chunk in enumerate(text_chunks):
                # Create job for this chunk
                # Count tokens in the chunk
                chunk_token_count = count_tokens(chunk, model)
                
                job_data = JobCreate(
                    name=f"{agent_name}-pdf-chunk-{i+1}",
                    user_id=user_id,
                    provider=provider,
                    model=model,
                    status="created",
                    client_ip=client_ip,
                    token_count=chunk_token_count
                )
                
                job = await JobService.create_job(db, job_data)
                job_ids.append(job.id)
                
                # Track start time for duration calculation
                start_time = time.time()
                
                # Prepare AI request by combining agent configuration with PDF chunk
                # Apply parameters to the agent task if provided
                processed_task = agent.task
                if parameters:
                    # Process parameters into the task using efficient string joining
                    param_lines = [f"{key}: {value}" for key, value in parameters.items()]
                    param_context = "\n".join(param_lines)
                    processed_task = f"{agent.task}\n\nParameters:\n{param_context}"
                
                chunk_context = f"This is part {i+1} of {len(text_chunks)} from a PDF document '{pdf_file.filename}'."
                if len(text_chunks) > 1:
                    chunk_context += f"\n\nPlease analyze this section and provide insights that can be combined with other sections:"
                
                combined_message = f"{agent.role}\n\n{processed_task}\n\n{chunk_context}\n\nDocument content:\n{chunk}"
                
                ai_request = aiapirequest(
                    job_id=job.id,
                    user_id=user_id,
                    model=model,
                    message=combined_message
                )
                
                # Update job status to processing
                await JobService.update_job_status(db, job.id, "processing")
                await db.commit()
                
                try:
                    # Send request to AI provider
                    ai_result = await send_ai_request(ai_request, provider, db)
                    
                    # Record the request and token usage for rate limiting (per chunk)
                    from service.rate_limit_service import RateLimitService
                    await RateLimitService.record_request(db, current_user, ai_result.tokens_used)
                    
                    # Calculate duration in milliseconds
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    if ai_result.success:
                        chunk_results.append(ai_result.content)
                        await JobService.update_job_status(db, job.id, "completed")
                        await JobService.update_job_duration(db, job.id, duration_ms)
                    else:
                        error_msg = ai_result.error_message or "AI processing failed"
                        chunk_results.append(f"Error processing chunk {i+1}: {error_msg}")
                        await JobService.update_job_status(db, job.id, "failed")
                        await JobService.update_job_duration(db, job.id, duration_ms)
                    
                    await db.commit()
                    
                except Exception as ai_error:
                    # Calculate duration even on error
                    duration_ms = int((time.time() - start_time) * 1000)
                    error_msg = f"Error processing chunk {i+1}: {str(ai_error)}"
                    chunk_results.append(error_msg)
                    
                    await JobService.update_job_status(db, job.id, "failed")
                    await JobService.update_job_duration(db, job.id, duration_ms)
                    await db.commit()
            
            break  # Exit the async for loop
        
        # Merge results from all chunks
        if len(text_chunks) > 1:
            # Use AI to merge results when we have multiple chunks
            merged_result = await _merge_results_with_ai(chunk_results, agent, provider, model, user_id, db)
        else:
            merged_result = chunk_results[0] if chunk_results else "No results generated"
        
        # Determine overall status
        failed_chunks = sum(1 for result in chunk_results if result.startswith("Error processing chunk"))
        if failed_chunks == len(chunk_results):
            overall_status = "failed"
        elif failed_chunks > 0:
            overall_status = "partially_completed"
        else:
            overall_status = "completed"
        
        return PDFAgentExecutionResponse(
            job_id=job_ids[0] if job_ids else "no-job",  # Return first job ID as primary
            agent=agent_name,
            provider=provider,
            model=model,
            status=overall_status,
            result=merged_result,
            chunks_processed=len(text_chunks),
            pdf_filename=pdf_file.filename
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def _merge_results_with_ai(chunk_results: List[str], agent, provider: str, model: str, user_id: str, db: Optional[AsyncSession] = None) -> str:
    """
    Use AI to intelligently merge results from multiple chunks
    """
    try:
        # Create a merging request
        merge_prompt = f"""You are an expert at synthesizing and merging analysis results. 

Your task is to combine the following analysis results from different sections of a document into a coherent, comprehensive final report.

The original analysis was performed by: {agent.name}
Agent task was: {agent.task}

Please merge these section results into a unified, well-structured final analysis:

"""
        
        for i, result in enumerate(chunk_results, 1):
            merge_prompt += f"\n--- Section {i} Analysis ---\n{result}\n"
        
        merge_prompt += """

Please provide a comprehensive merged analysis that:
1. Synthesizes key findings across all sections
2. Identifies common themes and patterns
3. Resolves any contradictions between sections
4. Provides a coherent final conclusion

Format your response as a well-structured report."""
        
        # Create merge request
        merge_request = aiapirequest(
            job_id=f"merge-{int(time.time())}",
            user_id=user_id,
            model=model,
            message=merge_prompt
        )
        
        # Send to AI service
        merge_result = await send_ai_request(merge_request, provider, db)
        
        if merge_result.success:
            return merge_result.content
        else:
            # Fallback to simple concatenation if AI merge fails
            return PDFService.merge_chunk_results(chunk_results, agent.name)
            
    except Exception as e:
        # Fallback to simple concatenation on any error
        return PDFService.merge_chunk_results(chunk_results, agent.name)


@app.post("/agent/execute-docx", response_model=DocxAgentExecutionResponse)
async def execute_agent_docx(
    http_request: Request,
    agent_name: str = Form(...),
    provider: str = Form(...),
    model: str = Form(...),
    user_id: str = Form(...),
    chunk_size: int = Form(4000),
    docx_file: UploadFile = File(...),
    current_user: User = Depends(authenticate_user_by_token)
):
    """
    Execute an agent with a DOCX file instead of text message
    
    This endpoint:
    1. Loads the agent configuration from YAML file
    2. Extracts text from the uploaded DOCX file
    3. Splits large text into chunks if needed (respecting token limits)
    4. Processes each chunk through the agent
    5. Merges results from all chunks into a final response
    6. Returns structured response with job details and merged result
    """
    try:
        # Extract client IP
        client_ip = get_client_ip(http_request)
        # Validate DOCX file
        if not docx_file.filename.lower().endswith('.docx'):
            raise HTTPException(
                status_code=400,
                detail="File must be a DOCX (.docx extension required)"
            )
        
        # Additional MIME type validation for security
        if docx_file.content_type and not docx_file.content_type in [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/octet-stream'  # Some browsers may send this for .docx
        ]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Expected DOCX document."
            )
        
        # Load agent configuration from YAML
        agent = await AgentService.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(
                status_code=404, 
                detail=f"Agent '{agent_name}' not found"
            )
        
        # Note: User-provided provider and model are accepted but ignored.
        # Always use the provider and model from the agent configuration.
        # Override with agent's configuration
        provider = agent.provider
        model = agent.model
        
        # Extract text from DOCX
        docx_text = await DocxService.extract_text_from_docx(docx_file)
        
        # Split text into chunks if needed
        text_chunks = DocxService.chunk_text(docx_text, chunk_size=chunk_size)
        
        # Process each chunk
        chunk_results = []
        job_ids = []
        
        async for db in get_async_session():
            for i, chunk in enumerate(text_chunks):
                # Create job for this chunk
                # Count tokens in the chunk
                chunk_token_count = count_tokens(chunk, model)
                
                job_data = JobCreate(
                    name=f"{agent_name}-docx-chunk-{i+1}",
                    user_id=user_id,
                    provider=provider,
                    model=model,
                    status="created",
                    client_ip=client_ip,
                    token_count=chunk_token_count
                )
                
                job = await JobService.create_job(db, job_data)
                job_ids.append(job.id)
                
                # Track start time for duration calculation
                start_time = time.time()
                
                # Prepare AI request by combining agent configuration with DOCX chunk
                # Sanitize filename to prevent prompt injection
                safe_filename = "".join(c for c in docx_file.filename if c.isalnum() or c in "._-")[:50]
                chunk_context = f"This is part {i+1} of {len(text_chunks)} from a DOCX document '{safe_filename}'."
                if len(text_chunks) > 1:
                    chunk_context += f"\n\nPlease analyze this section and provide insights that can be combined with other sections:"
                
                combined_message = f"{agent.role}\n\n{agent.task}\n\n{chunk_context}\n\nDocument content:\n{chunk}"
                
                ai_request = aiapirequest(
                    job_id=job.id,
                    user_id=user_id,
                    model=model,
                    message=combined_message
                )
                
                # Update job status to processing
                await JobService.update_job_status(db, job.id, "processing")
                await db.commit()
                
                try:
                    # Send request to AI provider
                    ai_result = await send_ai_request(ai_request, provider, db)
                    
                    # Record the request and token usage for rate limiting (per chunk)
                    from service.rate_limit_service import RateLimitService
                    await RateLimitService.record_request(db, current_user, ai_result.tokens_used)
                    
                    # Calculate duration in milliseconds
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    if ai_result.success:
                        chunk_results.append(ai_result.content)
                        await JobService.update_job_status(db, job.id, "completed")
                        await JobService.update_job_duration(db, job.id, duration_ms)
                    else:
                        error_msg = ai_result.error_message or "AI processing failed"
                        chunk_results.append(f"Error processing chunk {i+1}: {error_msg}")
                        await JobService.update_job_status(db, job.id, "failed")
                        await JobService.update_job_duration(db, job.id, duration_ms)
                    
                    await db.commit()
                    
                except Exception as ai_error:
                    # Calculate duration even on error
                    duration_ms = int((time.time() - start_time) * 1000)
                    error_msg = f"Error processing chunk {i+1}: {str(ai_error)}"
                    chunk_results.append(error_msg)
                    
                    await JobService.update_job_status(db, job.id, "failed")
                    await JobService.update_job_duration(db, job.id, duration_ms)
                    await db.commit()
            
            break  # Exit the async for loop
        
        # Merge results from all chunks
        if len(text_chunks) > 1:
            # Use AI to merge results when we have multiple chunks
            merged_result = await _merge_docx_results_with_ai(chunk_results, agent, provider, model, user_id, db)
        else:
            merged_result = chunk_results[0] if chunk_results else "No results generated"
        
        # Determine overall status
        failed_chunks = sum(1 for result in chunk_results if result.startswith("Error processing chunk"))
        if failed_chunks == len(chunk_results):
            overall_status = "failed"
        elif failed_chunks > 0:
            overall_status = "partially_completed"
        else:
            overall_status = "completed"
        
        return DocxAgentExecutionResponse(
            job_id=job_ids[0] if job_ids else "no-job",  # Return first job ID as primary
            agent=agent_name,
            provider=provider,
            model=model,
            status=overall_status,
            result=merged_result,
            chunks_processed=len(text_chunks),
            docx_filename=docx_file.filename
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def _merge_docx_results_with_ai(chunk_results: List[str], agent, provider: str, model: str, user_id: str, db: Optional[AsyncSession] = None) -> str:
    """
    Use AI to intelligently merge results from multiple DOCX chunks
    """
    try:
        # Create a merging request
        merge_prompt = f"""You are an expert at synthesizing and merging analysis results. 

Your task is to combine the following analysis results from different sections of a DOCX document into a coherent, comprehensive final report.

The original analysis was performed by: {agent.name}
Agent task was: {agent.task}

Please merge these section results into a unified, well-structured final analysis:

"""
        
        for i, result in enumerate(chunk_results, 1):
            merge_prompt += f"\n--- Section {i} Analysis ---\n{result}\n"
        
        merge_prompt += """

Please provide a comprehensive merged analysis that:
1. Synthesizes key findings across all sections
2. Identifies common themes and patterns
3. Resolves any contradictions between sections
4. Provides a coherent final conclusion

Format your response as a well-structured report."""
        
        # Create merge request
        merge_request = aiapirequest(
            job_id=f"merge-docx-{int(time.time())}",
            user_id=user_id,
            model=model,
            message=merge_prompt
        )
        
        # Send to AI service
        merge_result = await send_ai_request(merge_request, provider, db)
        
        if merge_result.success:
            return merge_result.content
        else:
            # Fallback to simple concatenation if AI merge fails
            return DocxService.merge_chunk_results(chunk_results, agent.name)
            
    except Exception as e:
        # Fallback to simple concatenation on any error
        return DocxService.merge_chunk_results(chunk_results, agent.name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    