from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.openapi.utils import get_openapi
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
import yaml
import time

from database import init_db, close_db
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
from service.agent_service import AgentService
from service.job_service import JobService
from service.ai_service import send_ai_request
from service.github_service import GitHubService
from service.github_issue_processor import GitHubIssueProcessor
from service.pdf_service import PDFService
from service.docx_service import DocxService
from controller.api_openai import process_openai_request
from database import get_async_session
from controller.api_gemini import process_gemini_request
from controller.api_claude import process_claude_request
from pydantic import ValidationError

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(lifespan=lifespan)

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
async def execute_agent(request: AgentExecutionRequest, current_user: User = Depends(authenticate_user_by_token)):
    """
    Execute an agent with the specified configuration
    
    This endpoint:
    1. Loads the agent configuration from YAML file
    2. Creates a job in the database
    3. Combines agent role/task with user message
    4. Routes request to appropriate AI provider
    5. Returns structured response with job details and result
    Rate limited by RPM and TPM.
    """
    from service.rate_limit_service import RateLimitService
    
    try:
        # Load agent configuration from YAML
        agent = await AgentService.get_agent_by_name(request.agent_name)
        if not agent:
            raise HTTPException(
                status_code=404, 
                detail=f"Agent '{request.agent_name}' not found"
            )
        
        # Validate provider matches agent configuration
        if request.provider.lower() != agent.provider.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{request.provider}' does not match agent configuration '{agent.provider}'"
            )
        
        # Validate model matches agent configuration  
        if request.model.lower() != agent.model.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.model}' does not match agent configuration '{agent.model}'"
            )
        
        # Create job in database
        async for db in get_async_session():
            job_data = JobCreate(
                name=f"{request.agent_name}-job",
                user_id=request.user_id,
                provider=request.provider,
                model=request.model,
                status="created"
            )
            
            job = await JobService.create_job(db, job_data)
            
            # Track start time for duration calculation
            start_time = time.time()
            
            # Prepare AI request by combining agent configuration with user message
            # Apply parameters to the agent task if provided
            processed_task = agent.task
            if request.parameters:
                # Process parameters into the task using efficient string joining
                param_lines = [f"{key}: {value}" for key, value in request.parameters.items()]
                param_context = "\n".join(param_lines)
                processed_task = f"{agent.task}\n\nParameters:\n{param_context}"
            
            combined_message = f"{agent.role}\n\n{processed_task}\n\nUser message: {request.message}"
            
            ai_request = aiapirequest(
                job_id=job.id,
                user_id=request.user_id,
                model=request.model,
                message=combined_message
            )
            
            # Update job status to processing
            await JobService.update_job_status(db, job.id, "processing")
            await db.commit()
            
            try:
                # Send request to AI provider
                ai_result = await send_ai_request(ai_request, request.provider)
                
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
                
                return AgentExecutionResponse(
                    job_id=job.id,
                    agent=request.agent_name,
                    provider=request.provider,
                    model=request.model,
                    status=status,
                    result=result
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
        
        # Validate provider matches agent configuration
        if provider.lower() != agent.provider.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider}' does not match agent configuration '{agent.provider}'"
            )
        
        # Validate model matches agent configuration  
        if model.lower() != agent.model.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' does not match agent configuration '{agent.model}'"
            )
        
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
                job_data = JobCreate(
                    name=f"{agent_name}-pdf-chunk-{i+1}",
                    user_id=user_id,
                    provider=provider,
                    model=model,
                    status="created"
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
                    ai_result = await send_ai_request(ai_request, provider)
                    
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
            merged_result = await _merge_results_with_ai(chunk_results, agent, provider, model, user_id)
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


async def _merge_results_with_ai(chunk_results: List[str], agent, provider: str, model: str, user_id: str) -> str:
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
        merge_result = await send_ai_request(merge_request, provider)
        
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
        
        # Validate provider matches agent configuration
        if provider.lower() != agent.provider.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider}' does not match agent configuration '{agent.provider}'"
            )
        
        # Validate model matches agent configuration  
        if model.lower() != agent.model.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' does not match agent configuration '{agent.model}'"
            )
        
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
                job_data = JobCreate(
                    name=f"{agent_name}-docx-chunk-{i+1}",
                    user_id=user_id,
                    provider=provider,
                    model=model,
                    status="created"
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
                    ai_result = await send_ai_request(ai_request, provider)
                    
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
            merged_result = await _merge_docx_results_with_ai(chunk_results, agent, provider, model, user_id)
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


async def _merge_docx_results_with_ai(chunk_results: List[str], agent, provider: str, model: str, user_id: str) -> str:
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
        merge_result = await send_ai_request(merge_request, provider)
        
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
    