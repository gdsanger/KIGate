"""
Admin panel routes for KIGate API
"""
import logging
from typing import Optional
from urllib.parse import quote
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct

from database import get_async_session
from model.user import User, UserCreate, UserUpdate
from model.agent import Agent, AgentCreate, AgentUpdate
from model.job import Job

from model.application_user import ApplicationUser, ApplicationUserCreate, ApplicationUserUpdate, ApplicationUserPasswordChange
from model.ai_agent_generator import AgentGenerationRequest, AgentGenerationResponse, AgentGenerationReview
from model.repository import Repository, RepositoryCreate, RepositoryUpdate
from model.provider import ProviderCreate, ProviderUpdate, ProviderModelUpdate, ProviderModel

from service.user_service import UserService
from service.agent_service import AgentService
from service.job_service import JobService
from service.application_user_service import ApplicationUserService
from service.ai_agent_generator_service import AIAgentGeneratorService
from service.repository_service import RepositoryService, GitHubSyncError
from service.provider_service import ProviderService
import yaml
from service.ai_service import send_ai_request
from model.aiapirequest import aiapirequest
from admin_auth import get_admin_user, admin_login_page
import uuid
import time
import html
import re

admin_router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


async def _enrich_jobs_with_costs(db: AsyncSession, jobs: list):
    """
    Enrich jobs with cost information based on token counts and model pricing.
    Adds 'estimated_cost' field to each job dict.
    """
    # Get all provider models with pricing information
    provider_models_result = await db.execute(
        select(ProviderModel).where(
            ProviderModel.input_price_per_million.isnot(None),
            ProviderModel.output_price_per_million.isnot(None)
        )
    )
    provider_models = provider_models_result.scalars().all()
    
    # Create a lookup map: model_id -> pricing info
    model_pricing = {}
    for pm in provider_models:
        model_pricing[pm.model_id] = {
            'input_price': pm.input_price_per_million,
            'output_price': pm.output_price_per_million
        }
    
    # Calculate cost for each job
    for job in jobs:
        estimated_cost = None
        
        # Check if we have pricing for this model
        if job['model'] in model_pricing:
            pricing = model_pricing[job['model']]
            input_tokens = job.get('token_count', 0) or 0
            output_tokens = job.get('output_token_count', 0) or 0
            
            # Calculate cost: (tokens / 1,000,000) * price_per_million
            input_cost = (input_tokens / 1_000_000) * pricing['input_price']
            output_cost = (output_tokens / 1_000_000) * pricing['output_price']
            estimated_cost = input_cost + output_cost
        
        # Add to job dict with 4 decimal places
        job['estimated_cost'] = estimated_cost


@admin_router.get("/login", response_class=HTMLResponse)
async def admin_login_route(request: Request):
    """Admin login page"""
    return await admin_login_page(request)


@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Admin dashboard"""
    # Get statistics
    user_count_result = await db.execute(select(func.count(User.client_id)))
    user_count = user_count_result.scalar()
    
    active_user_count_result = await db.execute(
        select(func.count(User.client_id)).where(User.is_active == True)
    )
    active_user_count = active_user_count_result.scalar()
    
    # Get agent count
    agents = await AgentService.get_all_agents()
    agent_count = len(agents)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_count": user_count,
        "active_user_count": active_user_count,
        "agent_count": agent_count
    })


@admin_router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request, 
    db: AsyncSession = Depends(get_async_session),
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """User management page"""
    users = await UserService.get_users_with_secrets(db)
    
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users,
        "message": message,
        "message_type": message_type
    })


@admin_router.post("/users/create")
async def create_user(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
    email: Optional[str] = Form(None),
    role: str = Form("user"),
    is_active: bool = Form(False),
    admin_user: str = Depends(get_admin_user)
):
    """Create new user"""
    try:
        user_data = UserCreate(
            name=name,
            email=email if email else None,
            role=role,
            is_active=is_active
        )
        
        new_user = await UserService.create_user(db, user_data)
        await db.commit()
        
        # Redirect with success message
        return RedirectResponse(
            url=f"/admin/users?message=Benutzer wurde erfolgreich erstellt. Client ID: {new_user.client_id}&message_type=success",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/users?message=Fehler beim Erstellen des Benutzers: {str(e)}&message_type=danger",
            status_code=303
        )


@admin_router.get("/api/users/{client_id}")
async def get_user_api(
    client_id: str, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Get user data for API"""
    user = await UserService.get_user(db, client_id)
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    return user


@admin_router.post("/users/{client_id}/update")
async def update_user(
    client_id: str,
    db: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
    email: Optional[str] = Form(None),
    role: str = Form("user"),
    is_active: bool = Form(False),
    admin_user: str = Depends(get_admin_user)
):
    """Update user"""
    try:
        user_data = UserUpdate(
            name=name,
            email=email if email else None,
            role=role,
            is_active=is_active
        )
        
        updated_user = await UserService.update_user(db, client_id, user_data)
        if not updated_user:
            return RedirectResponse(
                url=f"/admin/users?message=Benutzer nicht gefunden&message_type=danger",
                status_code=303
            )
        
        await db.commit()
        
        return RedirectResponse(
            url=f"/admin/users?message=Benutzer wurde erfolgreich aktualisiert&message_type=success",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/users?message=Fehler beim Aktualisieren des Benutzers: {str(e)}&message_type=danger",
            status_code=303
        )


@admin_router.post("/users/{client_id}/regenerate-secret")
async def regenerate_secret(
    client_id: str, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Regenerate client secret"""
    try:
        new_secret = await UserService.regenerate_client_secret(db, client_id)
        if not new_secret:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({"client_secret": new_secret})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/users/{client_id}/toggle-status")
async def toggle_user_status(
    client_id: str, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Toggle user active status"""
    try:
        updated_user = await UserService.toggle_user_status(db, client_id)
        if not updated_user:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({"is_active": updated_user.is_active})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.delete("/users/{client_id}")
async def delete_user(
    client_id: str, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Delete user"""
    try:
        success = await UserService.delete_user(db, client_id)
        if not success:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({"message": "Benutzer wurde gelöscht"})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Agent Management Routes
@admin_router.get("/agents", response_class=HTMLResponse)
async def admin_agents(
    request: Request, 
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """Agent management page"""
    agents = await AgentService.get_all_agents()
    
    return templates.TemplateResponse("agents.html", {
        "request": request,
        "agents": agents,
        "message": message,
        "message_type": message_type
    })


@admin_router.post("/agents/create")
async def create_agent(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    role: str = Form(...),
    provider: str = Form(...),
    model: str = Form(...),
    task: str = Form(...),
    parameters: Optional[str] = Form(None),
    admin_user: str = Depends(get_admin_user)
):
    """Create new agent"""
    try:
        # Parse parameters YAML if provided
        parsed_parameters = None
        if parameters and parameters.strip():
            import yaml
            try:
                parsed_parameters = yaml.safe_load(parameters.strip())
            except yaml.YAMLError as e:
                return RedirectResponse(
                    url=f"/admin/agents?message={quote(f'Fehler beim Parsen der Parameter: {str(e)}')}&message_type=danger",
                    status_code=303
                )
        
        agent_data = AgentCreate(
            name=name,
            description=description,
            role=role,
            provider=provider,
            model=model,
            task=task,
            parameters=parsed_parameters
        )
        
        await AgentService.create_agent(agent_data)
        
        return RedirectResponse(
            url=f"/admin/agents?message=Agent wurde erfolgreich erstellt&message_type=success",
            status_code=303
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin/agents?message={quote(str(e))}&message_type=danger",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/agents?message={quote('Fehler beim Erstellen des Agenten')}&message_type=danger",
            status_code=303
        )


@admin_router.get("/agents/new", response_class=HTMLResponse)
async def new_agent_page(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """New agent page"""
    providers = await ProviderService.get_all_providers(db, include_models=False)
    active_providers = [p for p in providers if p.is_active]
    
    return templates.TemplateResponse("agent_form.html", {
        "request": request,
        "mode": "create",
        "agent": None,
        "providers": active_providers
    })


@admin_router.get("/agents/{name}/edit", response_class=HTMLResponse)
async def edit_agent_page(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Edit agent page"""
    agent = await AgentService.get_agent_by_name(name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent nicht gefunden")
    
    providers = await ProviderService.get_all_providers(db, include_models=False)
    active_providers = [p for p in providers if p.is_active]
    
    return templates.TemplateResponse("agent_form.html", {
        "request": request,
        "mode": "edit",
        "agent": agent,
        "providers": active_providers
    })


@admin_router.get("/api/agents/{name}")
async def get_agent_api(
    name: str, 
    admin_user: str = Depends(get_admin_user)
):
    """Get agent data for API"""
    agent = await AgentService.get_agent_by_name(name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent nicht gefunden")
    
    return agent.dict()


@admin_router.post("/agents/{name}/update")
async def update_agent(
    name: str,
    new_name: str = Form(..., alias="name"),
    description: str = Form(...),
    role: str = Form(...),
    provider: str = Form(...),
    model: str = Form(...),
    task: str = Form(...),
    parameters: Optional[str] = Form(None),
    admin_user: str = Depends(get_admin_user)
):
    """Update agent"""
    try:
        # Parse parameters YAML if provided
        parsed_parameters = None
        if parameters and parameters.strip():
            import yaml
            try:
                parsed_parameters = yaml.safe_load(parameters.strip())
            except yaml.YAMLError as e:
                return RedirectResponse(
                    url=f"/admin/agents?message={quote(f'Fehler beim Parsen der Parameter: {str(e)}')}&message_type=danger",
                    status_code=303
                )
        
        agent_data = AgentUpdate(
            name=new_name,
            description=description,
            role=role,
            provider=provider,
            model=model,
            task=task,
            parameters=parsed_parameters
        )
        
        updated_agent = await AgentService.update_agent(name, agent_data)
        if not updated_agent:
            raise HTTPException(status_code=404, detail="Agent nicht gefunden")
        
        return RedirectResponse(
            url=f"/admin/agents?message=Agent wurde erfolgreich aktualisiert&message_type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/agents?message={quote('Fehler beim Aktualisieren des Agenten')}&message_type=danger",
            status_code=303
        )


@admin_router.post("/agents/{name}/clone")
async def clone_agent(
    name: str,
    admin_user: str = Depends(get_admin_user)
):
    """Clone agent"""
    try:
        cloned_agent = await AgentService.clone_agent(name)
        return JSONResponse({
            "message": "Agent wurde geklont",
            "cloned_agent": cloned_agent.dict()
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.delete("/agents/{name}")
async def delete_agent(
    name: str, 
    admin_user: str = Depends(get_admin_user)
):
    """Delete agent"""
    try:
        success = await AgentService.delete_agent(name)
        if not success:
            raise HTTPException(status_code=404, detail="Agent nicht gefunden")
        
        return JSONResponse({"message": "Agent wurde gelöscht"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# AI Agent Generation Routes
@admin_router.get("/agents/ai-create", response_class=HTMLResponse)
async def ai_create_agent_page(
    request: Request,
    description: Optional[str] = None,
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """AI-powered agent creation page"""
    return templates.TemplateResponse("ai_agent_create.html", {
        "request": request,
        "description": description,
        "message": message,
        "message_type": message_type
    })


@admin_router.post("/agents/ai-generate")
async def ai_generate_agent(
    request: Request,
    description: str = Form(...),
    admin_user: str = Depends(get_admin_user)
):
    """Generate agent configuration using AI"""
    try:
        # Validate description
        if not description or len(description.strip()) < 10:
            return RedirectResponse(
                url=f"/admin/agents/ai-create?message={quote('Beschreibung muss mindestens 10 Zeichen lang sein')}&message_type=danger",
                status_code=303
            )
        
        # Generate agent config using AI
        generation_request = AgentGenerationRequest(description=description.strip())
        generated_config = await AIAgentGeneratorService.generate_agent_config(generation_request)
        
        if not generated_config:
            return RedirectResponse(
                url=f"/admin/agents/ai-create?message={quote('Fehler bei der AI-Generierung. Bitte versuchen Sie es erneut oder passen Sie Ihre Beschreibung an.')}&message_type=danger",
                status_code=303
            )
        
        # Convert parameters to YAML for the review form
        parameters_yaml = AIAgentGeneratorService.convert_parameters_to_yaml(generated_config.parameters)
        
        return templates.TemplateResponse("ai_agent_review.html", {
            "request": request,
            "generated_config": generated_config,
            "parameters_yaml": parameters_yaml,
            "user_description": description.strip()
        })
        
    except Exception as e:
        logger.error(f"Error in AI agent generation: {e}")
        return RedirectResponse(
            url=f"/admin/agents/ai-create?message={quote('Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.')}&message_type=danger",
            status_code=303
        )


@admin_router.post("/agents/ai-review")
async def ai_review_agent(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    role: str = Form(...),
    provider: str = Form(...),
    model: str = Form(...),
    task: str = Form(...),
    parameters: Optional[str] = Form(None),
    user_description: str = Form(...),
    action: str = Form(...),  # "accept" or "regenerate"
    admin_user: str = Depends(get_admin_user)
):
    """Handle AI agent review - accept or regenerate"""
    try:
        if action == "regenerate":
            # Redirect back to generation with the original description
            return RedirectResponse(
                url=f"/admin/agents/ai-create?description={quote(user_description)}&message={quote('Neue Generierung gestartet. Sie können Ihre Beschreibung anpassen.')}&message_type=info",
                status_code=303
            )
        
        elif action == "accept":
            # Parse parameters YAML if provided
            parsed_parameters = None
            if parameters and parameters.strip():
                try:
                    # Limit YAML content size to prevent YAML bombs
                    yaml_content = parameters.strip()
                    if len(yaml_content) > 10000:  # 10KB limit
                        return RedirectResponse(
                            url=f"/admin/agents/ai-create?message={quote('Parameter-YAML ist zu groß (max. 10KB)')}&message_type=danger",
                            status_code=303
                        )
                    parsed_parameters = yaml.safe_load(yaml_content)
                except yaml.YAMLError as e:
                    return RedirectResponse(
                        url=f"/admin/agents/ai-create?message={quote(f'Fehler beim Parsen der Parameter: {str(e)}')}&message_type=danger",
                        status_code=303
                    )
            
            # Create the agent
            agent_data = AgentCreate(
                name=name,
                description=description,
                role=role,
                provider=provider,
                model=model,
                task=task,
                parameters=parsed_parameters
            )
            
            await AgentService.create_agent(agent_data)
            
            return RedirectResponse(
                url=f"/admin/agents?message={quote('AI-generierter Agent wurde erfolgreich erstellt!')}&message_type=success",
                status_code=303
            )
        
        else:
            return RedirectResponse(
                url=f"/admin/agents/ai-create?message={quote('Ungültige Aktion')}&message_type=danger",
                status_code=303
            )
            
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin/agents?message={quote(str(e))}&message_type=danger",
            status_code=303
        )
    except Exception as e:
        logger.error(f"Error in AI agent review: {e}")
        return RedirectResponse(
            url=f"/admin/agents/ai-create?message={quote('Fehler beim Erstellen des Agenten')}&message_type=danger",
            status_code=303
        )
@admin_router.post("/agents/{name}/test")
async def test_agent(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Test agent with real AI API call"""
    # Get agent configuration
    agent = await AgentService.get_agent_by_name(name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent nicht gefunden")
    
    try:
        # Parse request body
        body = await request.json()
        message = body.get('message', '').strip()
        parameters = body.get('parameters') or {}
        
        if not message:
            return JSONResponse({
                "success": False,
                "error": "Nachricht ist erforderlich"
            })
        
        # Validate and sanitize parameters to prevent prompt injection
        sanitized_parameters = {}
        if parameters:
            for key, value in parameters.items():
                # Sanitize parameter key and value
                clean_key = re.sub(r'[^\w\-_]', '', str(key))[:50]  # Only allow alphanumeric, dash, underscore
                clean_value = html.escape(str(value)[:500])  # Escape HTML and limit length
                if clean_key and clean_value.strip():
                    sanitized_parameters[clean_key] = clean_value
        
        # Generate a test job ID
        test_job_id = str(uuid.uuid4())
        test_user_id = f"admin-test-{admin_user}"
        
        # Prepare AI request by combining agent configuration with user message
        processed_task = agent.task
        if sanitized_parameters:
            # Process sanitized parameters into the task
            param_lines = [f"{key}: {value}" for key, value in sanitized_parameters.items()]
            param_context = "\n".join(param_lines)
            processed_task = f"{agent.task}\n\nParameter:\n{param_context}"
        
        combined_message = f"{agent.role}\n\n{processed_task}\n\nBenutzer-Nachricht: {message}"
        
        ai_request = aiapirequest(
            job_id=test_job_id,
            user_id=test_user_id,
            model=agent.model,
            message=combined_message
        )
        
        # Track start time
        start_time = time.time()
        
        # Send request to AI provider
        ai_result = await send_ai_request(ai_request, agent.provider, db)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        if ai_result.success:
            return JSONResponse({
                "success": True,
                "result": ai_result.content,
                "duration_ms": duration_ms,
                "provider": agent.provider,
                "model": agent.model
            })
        else:
            return JSONResponse({
                "success": False,
                "error": ai_result.error_message or "AI-Verarbeitung fehlgeschlagen",
                "duration_ms": duration_ms,
                "provider": agent.provider,
                "model": agent.model
            })
            
    except Exception as e:
        logger.error(f"Error testing agent {name}: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Fehler beim Testen des Agenten: {str(e)}"
        })


# Job Management Routes
@admin_router.get("/jobs", response_class=HTMLResponse)
async def admin_jobs(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    provider: Optional[str] = None,
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Job management page with pagination and filters"""
    try:
        # Ensure page is at least 1
        page = max(1, page)
        
        # Get jobs with pagination and filters
        jobs, total_count = await JobService.get_jobs_paginated(
            db, 
            page=page, 
            per_page=25,
            status_filter=status,
            provider_filter=provider,
            name_filter=name
        )
        
        # Calculate pagination info
        total_pages = (total_count + 24) // 25  # Ceiling division
        has_prev = page > 1
        has_next = page < total_pages
        
        # Get unique values for filters
        # Get distinct statuses
        status_result = await db.execute(select(distinct(Job.status)).order_by(Job.status))
        statuses = [s for s in status_result.scalars().all() if s]
        
        # Get distinct providers
        provider_result = await db.execute(select(distinct(Job.provider)).order_by(Job.provider))
        providers = [p for p in provider_result.scalars().all() if p]
        
        # Enrich jobs with cost information
        await _enrich_jobs_with_costs(db, jobs)
        
        return templates.TemplateResponse("jobs.html", {
            "request": request,
            "jobs": jobs,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_page": page - 1 if has_prev else None,
            "next_page": page + 1 if has_next else None,
            "statuses": statuses,
            "providers": providers,
            "current_status": status,
            "current_provider": provider,
            "current_name": name,
        })
        
    except Exception as e:
        logger.error(f"Error loading jobs page: {str(e)}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Jobs")


@admin_router.post("/jobs/cleanup")
async def cleanup_old_jobs(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Delete jobs older than 7 days"""
    try:
        deleted_count = await JobService.delete_old_jobs(db, days=7)
        await db.commit()
        
        return JSONResponse({
            "success": True,
            "deleted_count": deleted_count,
            "message": f"{deleted_count} Jobs wurden gelöscht"
        })
    except Exception as e:
        await db.rollback()
        logger.error(f"Error cleaning up old jobs: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "Fehler beim Bereinigen der Jobs"
        }, status_code=500)


# ApplicationUser Management Routes
@admin_router.get("/application-users", response_class=HTMLResponse)
async def admin_application_users(
    request: Request, 
    db: AsyncSession = Depends(get_async_session),
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """ApplicationUser management page"""
    application_users = await ApplicationUserService.get_all_users(db)
    
    return templates.TemplateResponse("application_users.html", {
        "request": request,
        "application_users": application_users,
        "message": message,
        "message_type": message_type
    })


@admin_router.post("/application-users/create")
async def create_application_user(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
    email: str = Form(...),
    password: Optional[str] = Form(None),
    role: str = Form("user"),
    is_active: bool = Form(False),
    admin_user: str = Depends(get_admin_user)
):
    """Create new application user"""
    try:
        user_data = ApplicationUserCreate(
            name=name,
            email=email,
            password=password if password else None,
            role=role,
            is_active=is_active
        )
        
        new_user = await ApplicationUserService.create_user(db, user_data)
        await db.commit()
        
        # Create success message with generated password if applicable
        success_msg = f"Admin-Benutzer wurde erfolgreich erstellt."
        if new_user.generated_password:
            success_msg += f" Generiertes Passwort: {new_user.generated_password} (E-Mail wurde versendet)"
        
        # Redirect with success message
        return RedirectResponse(
            url=f"/admin/application-users?message={quote(success_msg)}&message_type=success",
            status_code=303
        )
    except ValueError as ve:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/application-users?message={quote(str(ve))}&message_type=danger",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/application-users?message={quote(f'Fehler beim Erstellen des Admin-Benutzers: {str(e)}')}&message_type=danger",
            status_code=303
        )


@admin_router.get("/api/application-users/{user_id}")
async def get_application_user_api(
    user_id: str, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Get application user data for API"""
    user = await ApplicationUserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Admin-Benutzer nicht gefunden")
    return user


@admin_router.post("/application-users/{user_id}/update")
async def update_application_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form("user"),
    is_active: bool = Form(False),
    admin_user: str = Depends(get_admin_user)
):
    """Update application user"""
    try:
        user_data = ApplicationUserUpdate(
            name=name,
            email=email,
            role=role,
            is_active=is_active
        )
        
        updated_user = await ApplicationUserService.update_user(db, user_id, user_data)
        if not updated_user:
            return RedirectResponse(
                url=f"/admin/application-users?message={quote('Admin-Benutzer nicht gefunden')}&message_type=danger",
                status_code=303
            )
        
        await db.commit()
        
        return RedirectResponse(
            url=f"/admin/application-users?message={quote('Admin-Benutzer wurde erfolgreich aktualisiert')}&message_type=success",
            status_code=303
        )
    except ValueError as ve:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/application-users?message={quote(str(ve))}&message_type=danger",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/application-users?message={quote(f'Fehler beim Aktualisieren des Admin-Benutzers: {str(e)}')}&message_type=danger",
            status_code=303
        )


@admin_router.post("/application-users/{user_id}/reset-password")
async def reset_application_user_password(
    user_id: str, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Reset application user password"""
    try:
        result = await ApplicationUserService.reset_password(db, user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Admin-Benutzer nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({
            "message": "Passwort wurde zurückgesetzt",
            "new_password": result.generated_password
        })
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/application-users/{user_id}/change-password")
async def change_application_user_password(
    user_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_password: str = Form(...),
    new_password: str = Form(...),
    admin_user: str = Depends(get_admin_user)
):
    """Change application user password"""
    try:
        updated_user = await ApplicationUserService.change_password(
            db, user_id, current_password, new_password
        )
        if not updated_user:
            raise HTTPException(status_code=404, detail="Admin-Benutzer nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({"message": "Passwort wurde erfolgreich geändert"})
    except ValueError as ve:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/application-users/{user_id}/toggle-status")
async def toggle_application_user_status(
    user_id: str, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Toggle application user active status"""
    try:
        updated_user = await ApplicationUserService.toggle_user_status(db, user_id)
        if not updated_user:
            raise HTTPException(status_code=404, detail="Admin-Benutzer nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({"is_active": updated_user.is_active})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.delete("/application-users/{user_id}")
async def delete_application_user(
    user_id: str, 
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Delete application user"""
    try:
        success = await ApplicationUserService.delete_user(db, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Admin-Benutzer nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({"message": "Admin-Benutzer wurde gelöscht"})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# GitHub Issue Creation Routes
@admin_router.get("/github-issues", response_class=HTMLResponse)
async def admin_github_issues(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_async_session),
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """GitHub issue creation and history page"""
    from model.github_issue_record import GitHubIssueRecord
    
    try:
        # Ensure page is at least 1
        page = max(1, page)
        per_page = 20
        offset = (page - 1) * per_page
        
        # Get GitHub issue records with pagination
        result = await db.execute(
            select(GitHubIssueRecord)
            .order_by(GitHubIssueRecord.created_at.desc())
            .limit(per_page)
            .offset(offset)
        )
        github_issues = result.scalars().all()
        
        # Get total count
        count_result = await db.execute(
            select(func.count(GitHubIssueRecord.id))
        )
        total_count = count_result.scalar()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        return templates.TemplateResponse("github_issues.html", {
            "request": request,
            "github_issues": github_issues,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_page": page - 1 if has_prev else None,
            "next_page": page + 1 if has_next else None,
            "message": message,
            "message_type": message_type
        })
        
    except Exception as e:
        logger.error(f"Error loading GitHub issues page: {str(e)}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der GitHub Issues")


@admin_router.post("/github-issues/create")
async def create_github_issue_admin(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    repository: str = Form(...),
    issue_text: str = Form(...),
    admin_user: str = Depends(get_admin_user)
):
    """Create GitHub issue via admin panel"""
    from model.github_issue_record import GitHubIssueRecord
    from service.github_service import GitHubService
    from service.github_issue_processor import GitHubIssueProcessor
    
    try:
        # Validate repository format
        if not GitHubService.validate_repository_format(repository.strip()):
            return RedirectResponse(
                url=f"/admin/github-issues?message={quote('Ungültiges Repository-Format. Erwartet: owner/repo')}&message_type=danger",
                status_code=303
            )
        
        repository = repository.strip()
        issue_text = issue_text.strip()
        
        if not issue_text:
            return RedirectResponse(
                url=f"/admin/github-issues?message={quote('Issue-Text ist erforderlich')}&message_type=danger",
                status_code=303
            )
        
        # Create initial record
        github_issue_record = GitHubIssueRecord(
            repository=repository,
            original_text=issue_text,
            success=False,
            created_by=admin_user
        )
        db.add(github_issue_record)
        await db.flush()  # Get the ID
        
        try:
            # Process text with AI
            processed_content = await GitHubIssueProcessor.process_issue_text(
                text=issue_text,
                user_id=f"admin_{admin_user}",  # Use underscore for consistency with existing patterns
                provider="openai",
                model="gpt-3.5-turbo"
            )
            
            if processed_content:
                github_issue_record.processed_text = processed_content.improved_text
                github_issue_record.issue_title = processed_content.title
                
                # Create GitHub issue
                github_response = await GitHubService.create_issue(repository, processed_content)
                
                # Update record with results
                github_issue_record.issue_number = github_response.issue_number if github_response.success else None
                github_issue_record.issue_url = github_response.issue_url if github_response.success else None
                github_issue_record.success = github_response.success
                github_issue_record.error_message = github_response.error_message
                
                await db.commit()
                
                if github_response.success:
                    return RedirectResponse(
                        url=f"/admin/github-issues?message={quote(f'GitHub Issue #{github_response.issue_number} wurde erfolgreich erstellt!')}&message_type=success",
                        status_code=303
                    )
                else:
                    return RedirectResponse(
                        url=f"/admin/github-issues?message={quote(f'Fehler beim Erstellen des GitHub Issues: {github_response.error_message}')}&message_type=danger",
                        status_code=303
                    )
            else:
                github_issue_record.error_message = "AI-Textverarbeitung fehlgeschlagen"
                await db.commit()
                
                return RedirectResponse(
                    url=f"/admin/github-issues?message={quote('Fehler bei der AI-Textverarbeitung')}&message_type=danger",
                    status_code=303
                )
                
        except Exception as e:
            # Update record with error
            github_issue_record.error_message = str(e)
            await db.commit()
            
            return RedirectResponse(
                url=f"/admin/github-issues?message={quote(f'Fehler beim Erstellen des GitHub Issues: {str(e)}')}&message_type=danger",
                status_code=303
            )
            
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in GitHub issue creation: {str(e)}")
        return RedirectResponse(
            url=f"/admin/github-issues?message={quote('Unerwarteter Fehler beim Erstellen des GitHub Issues')}&message_type=danger",
            status_code=303
        )


# Repository Management Routes
@admin_router.get("/repositories", response_class=HTMLResponse)
async def admin_repositories(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """Repository management page"""
    repositories = await RepositoryService.get_all_repositories(db)
    
    return templates.TemplateResponse("repositories.html", {
        "request": request,
        "repositories": repositories,
        "message": message,
        "message_type": message_type
    })


@admin_router.post("/repositories/sync")
async def sync_repositories(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    username_or_org: str = Form(...),
    admin_user: str = Depends(get_admin_user)
):
    """Sync repositories from GitHub API"""
    try:
        synced_count = await RepositoryService.sync_repositories(db, username_or_org.strip())
        
        return RedirectResponse(
            url=f"/admin/repositories?message={quote(f'{synced_count} Repositories wurden erfolgreich synchronisiert für {username_or_org.strip()}!')}&message_type=success",
            status_code=303
        )
    except GitHubSyncError as e:
        logger.warning(f"GitHub sync error for {username_or_org}: {e}")
        message_type = "warning" if e.error_type in ["not_found", "no_repos"] else "danger"
        return RedirectResponse(
            url=f"/admin/repositories?message={quote(str(e))}&message_type={message_type}",
            status_code=303
        )
    except Exception as e:
        logger.error(f"Unexpected error syncing repositories for {username_or_org}: {str(e)}")
        return RedirectResponse(
            url=f"/admin/repositories?message={quote('Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut oder kontaktieren Sie den Administrator.')}&message_type=danger",
            status_code=303
        )


@admin_router.post("/repositories/{repo_id}/toggle-status")
async def toggle_repository_status(
    repo_id: int,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Toggle repository active status"""
    try:
        updated_repo = await RepositoryService.toggle_repository_status(db, repo_id)
        if not updated_repo:
            raise HTTPException(status_code=404, detail="Repository nicht gefunden")
        
        return JSONResponse({"is_active": updated_repo.is_active})
    except Exception as e:
        logger.error(f"Error toggling repository status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.delete("/repositories/{repo_id}")
async def delete_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Delete repository"""
    try:
        success = await RepositoryService.delete_repository(db, repo_id)
        if not success:
            raise HTTPException(status_code=404, detail="Repository nicht gefunden")
        
        return JSONResponse({"message": "Repository wurde gelöscht"})
    except Exception as e:
        logger.error(f"Error deleting repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# API endpoint to get active repositories for dropdown
@admin_router.get("/api/repositories/active")
async def get_active_repositories(
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Get active repositories for dropdown"""
    repositories = await RepositoryService.get_active_repositories(db)
    return [{"full_name": repo.full_name, "description": repo.description} for repo in repositories]


# Provider Management Routes
@admin_router.get("/providers", response_class=HTMLResponse)
async def admin_providers(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """Provider management page"""
    providers = await ProviderService.get_all_providers(db, include_models=True)
    
    return templates.TemplateResponse("providers.html", {
        "request": request,
        "providers": providers,
        "message": message,
        "message_type": message_type
    })


# Settings Management Routes
@admin_router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """Settings management page"""
    from service.settings_service import SettingsService
    settings = await SettingsService.get_all_settings(db)
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": settings,
        "message": message,
        "message_type": message_type
    })


@admin_router.post("/providers/create")
async def create_provider(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
    provider_type: str = Form(...),
    api_key: Optional[str] = Form(None),
    api_url: Optional[str] = Form(None),
    organization_id: Optional[str] = Form(None),
    is_active: bool = Form(False),
    admin_user: str = Depends(get_admin_user)
):
    """Create new provider"""
    try:
        provider_data = ProviderCreate(
            name=name,
            provider_type=provider_type,
            api_key=api_key if api_key else None,
            api_url=api_url if api_url else None,
            organization_id=organization_id if organization_id else None,
            is_active=is_active
        )
        
        await ProviderService.create_provider(db, provider_data)
        await db.commit()
        
        return RedirectResponse(
            url=f"/admin/providers?message=Provider wurde erfolgreich erstellt&message_type=success",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/providers?message={quote(f'Fehler beim Erstellen des Providers: {str(e)}')}&message_type=danger",
            status_code=303
        )


@admin_router.get("/api/providers/{provider_id}")
async def get_provider_api(
    provider_id: str,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Get provider data for API"""
    provider = await ProviderService.get_provider(db, provider_id, include_models=True)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider nicht gefunden")
    return provider


@admin_router.post("/providers/{provider_id}/update")
async def update_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
    api_key: Optional[str] = Form(None),
    api_url: Optional[str] = Form(None),
    organization_id: Optional[str] = Form(None),
    is_active: bool = Form(False),
    admin_user: str = Depends(get_admin_user)
):
    """Update provider"""
    try:
        provider_data = ProviderUpdate(
            name=name,
            api_key=api_key if api_key else None,
            api_url=api_url if api_url else None,
            organization_id=organization_id if organization_id else None,
            is_active=is_active
        )
        
        updated_provider = await ProviderService.update_provider(db, provider_id, provider_data)
        if not updated_provider:
            return RedirectResponse(
                url=f"/admin/providers?message=Provider nicht gefunden&message_type=danger",
                status_code=303
            )
        
        await db.commit()
        
        return RedirectResponse(
            url=f"/admin/providers?message=Provider wurde erfolgreich aktualisiert&message_type=success",
            status_code=303
        )
    except Exception as e:
        logger.error(f"Error updating provider: {str(e)}")
        return RedirectResponse(
            url=f"/admin/providers?message=Fehler beim Aktualisieren des Providers&message_type=danger",
            status_code=303
        )


@admin_router.post("/settings/update")
async def update_settings(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Update settings"""
    from service.settings_service import SettingsService
    from model.settings import SettingsUpdate
    
    try:
        # Parse form data
        form_data = await request.form()
        
        # Update each setting
        for key in form_data:
            if key.startswith("setting_"):
                setting_key = key.replace("setting_", "")
                value = form_data.get(key)
                
                # Check if this is a secret field
                is_secret_key = f"secret_{setting_key}"
                is_secret = is_secret_key in form_data
                
                # Update or create setting
                await SettingsService.upsert_setting(
                    db, 
                    setting_key, 
                    value,
                    is_secret=is_secret
                )
        
        await db.commit()
        
        # Reload Sentry if DSN was updated
        sentry_dsn = await SettingsService.get_setting_value(db, "sentry_dsn")
        if sentry_dsn:
            from logging_config import LoggingConfig
            sentry_env = await SettingsService.get_setting_value(db, "sentry_environment", "production")
            sentry_rate_str = await SettingsService.get_setting_value(db, "sentry_traces_sample_rate", "0.1")
            try:
                sentry_rate = float(sentry_rate_str)
            except (ValueError, TypeError):
                sentry_rate = 0.1
            
            LoggingConfig.setup_sentry(dsn=sentry_dsn, environment=sentry_env, 
                                      traces_sample_rate=sentry_rate)
        
        return RedirectResponse(
            url=f"/admin/settings?message={quote('Einstellungen wurden erfolgreich aktualisiert')}&message_type=success",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating settings: {str(e)}")
        return RedirectResponse(
            url=f"/admin/settings?message={quote(f'Fehler beim Aktualisieren der Einstellungen: {str(e)}')}&message_type=danger",
            status_code=303
        )


@admin_router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Delete provider"""
    try:
        success = await ProviderService.delete_provider(db, provider_id)
        if not success:
            raise HTTPException(status_code=404, detail="Provider nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({"message": "Provider wurde gelöscht"})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/providers/{provider_id}/fetch-models")
async def fetch_provider_models(
    provider_id: str,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Fetch models from provider API"""
    try:
        models = await ProviderService.fetch_models_from_api(db, provider_id)
        await db.commit()
        
        return JSONResponse({
            "message": f"{len(models)} Modelle wurden erfolgreich geladen",
            "models": [{"id": m.id, "name": m.model_name, "is_active": m.is_active} for m in models]
        })
    except Exception as e:
        await db.rollback()
        logger.error(f"Error fetching models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden der Modelle: {str(e)}")


@admin_router.post("/providers/{provider_id}/models/{model_id}/toggle")
async def toggle_provider_model(
    provider_id: str,
    model_id: str,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Toggle provider model active status"""
    try:
        # Get current model
        models = await ProviderService.get_provider_models(db, provider_id)
        model = next((m for m in models if m.id == model_id), None)
        
        if not model:
            raise HTTPException(status_code=404, detail="Model nicht gefunden")
        
        # Toggle status
        updated_model = await ProviderService.update_provider_model(
            db, 
            model_id, 
            ProviderModelUpdate(is_active=not model.is_active)
        )
        await db.commit()
        
        return JSONResponse({"is_active": updated_model.is_active})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/providers/{provider_id}/detail", response_class=HTMLResponse)
async def admin_provider_detail(
    provider_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    message: Optional[str] = None,
    message_type: Optional[str] = None,
    admin_user: str = Depends(get_admin_user)
):
    """Provider detail page with models management"""
    provider = await ProviderService.get_provider(db, provider_id, include_models=True)
    if not provider:
        return RedirectResponse(
            url=f"/admin/providers?message=Provider nicht gefunden&message_type=danger",
            status_code=303
        )
    
    return templates.TemplateResponse("provider_detail.html", {
        "request": request,
        "provider": provider,
        "message": message,
        "message_type": message_type
    })


@admin_router.post("/providers/{provider_id}/models/create")
async def create_provider_model(
    provider_id: str,
    db: AsyncSession = Depends(get_async_session),
    model_name: str = Form(...),
    model_id: str = Form(...),
    input_price_per_million: Optional[float] = Form(None),
    output_price_per_million: Optional[float] = Form(None),
    is_active: bool = Form(False),
    admin_user: str = Depends(get_admin_user)
):
    """Create new provider model"""
    try:
        from model.provider import ProviderModelCreate
        
        model_data = ProviderModelCreate(
            provider_id=provider_id,
            model_name=model_name,
            model_id=model_id,
            is_active=is_active,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million
        )
        
        await ProviderService.create_provider_model(db, model_data)
        await db.commit()
        
        return RedirectResponse(
            url=f"/admin/providers/{provider_id}/detail?message=Modell wurde erfolgreich erstellt&message_type=success",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating model: {str(e)}")
        return RedirectResponse(
            url=f"/admin/providers/{provider_id}/detail?message={quote(f'Fehler beim Erstellen des Modells: {str(e)}')}&message_type=danger",
            status_code=303
        )


@admin_router.post("/providers/{provider_id}/models/{model_id}/update")
async def update_provider_model_route(
    provider_id: str,
    model_id: str,
    db: AsyncSession = Depends(get_async_session),
    model_name: Optional[str] = Form(None),
    input_price_per_million: Optional[float] = Form(None),
    output_price_per_million: Optional[float] = Form(None),
    is_active: bool = Form(False),
    admin_user: str = Depends(get_admin_user)
):
    """Update provider model"""
    try:
        model_data = ProviderModelUpdate(
            model_name=model_name,
            is_active=is_active,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million
        )
        
        updated_model = await ProviderService.update_provider_model(db, model_id, model_data)
        if not updated_model:
            return RedirectResponse(
                url=f"/admin/providers/{provider_id}/detail?message=Modell nicht gefunden&message_type=danger",
                status_code=303
            )
        
        await db.commit()
        
        return RedirectResponse(
            url=f"/admin/providers/{provider_id}/detail?message=Modell wurde erfolgreich aktualisiert&message_type=success",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating model: {str(e)}")
        return RedirectResponse(
            url=f"/admin/providers/{provider_id}/detail?message=Fehler beim Aktualisieren des Modells&message_type=danger",
            status_code=303
        )


@admin_router.delete("/providers/{provider_id}/models/{model_id}")
async def delete_provider_model(
    provider_id: str,
    model_id: str,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Delete provider model"""
    try:
        success = await ProviderService.delete_provider_model(db, model_id)
        if not success:
            raise HTTPException(status_code=404, detail="Modell nicht gefunden")
        
        await db.commit()
        
        return JSONResponse({"message": "Modell wurde gelöscht"})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/api/providers")
async def get_all_providers_api(
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Get all active providers for dropdown"""
    providers = await ProviderService.get_all_providers(db, include_models=False)
    active_providers = [p for p in providers if p.is_active]
    return [{"id": p.id, "name": p.name, "provider_type": p.provider_type} for p in active_providers]


@admin_router.get("/api/providers/{provider_id}/models")
async def get_provider_models_api(
    provider_id: str,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Get active models for a provider"""
    models = await ProviderService.get_provider_models(db, provider_id, active_only=True)
    return [{"id": m.model_id, "name": m.model_name} for m in models]


@admin_router.get("/api/providers-for-agents")
async def get_providers_for_agents(
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """Get all active providers for agent creation/editing"""
    providers = await ProviderService.get_all_providers(db, include_models=False)
    active_providers = [p for p in providers if p.is_active]
    return [{"id": p.id, "name": p.name, "provider_type": p.provider_type} for p in active_providers]

# AI Audit Log Routes
@admin_router.get("/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_async_session),
    admin_user: str = Depends(get_admin_user)
):
    """AI Audit Log page with pagination"""
    from service.ai_audit_log_service import AIAuditLogService
    
    try:
        # Ensure page is at least 1
        page = max(1, page)
        per_page = 50
        
        # Get logs with pagination
        logs, total_count = await AIAuditLogService.get_logs_paginated(db, page=page, per_page=per_page)
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        return templates.TemplateResponse("audit_logs.html", {
            "request": request,
            "logs": logs,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_page": page - 1 if has_prev else None,
            "next_page": page + 1 if has_next else None,
        })
        
    except Exception as e:
        logger.error(f"Error loading audit logs page: {str(e)}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Audit Logs")

