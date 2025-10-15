from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import logging
import asyncio
import uuid
from datetime import datetime
import sys

# Add src to path to ensure imports work
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import your custom modules - these should now work with the fixed structure
from github.repo_manager import create_github_repo, update_github_repo
from github.pages_deployer import enable_github_pages, verify_pages_deployment
from generators.code_generator import generate_application_code
from generators.file_parser import parse_code_output
from evaluation.notifier import notify_evaluation_service
from utils.secret_verifier import verify_secret
from utils.attachment_handler import handle_attachments

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Software Development Engine",
    description="Automated application builder and deployer",
    version="1.0.0"
)

# Pydantic models for request/response
class Attachment(BaseModel):
    name: str
    url: str  # data URI

class BuildRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: List[str]
    evaluation_url: str
    attachments: List[Attachment]

class BuildResponse(BaseModel):
    status: str
    message: str
    request_id: Optional[str] = None

class EvaluationNotification(BaseModel):
    email: str
    task: str
    round: int
    nonce: str
    repo_url: Optional[str] = None
    commit_sha: Optional[str] = None
    pages_url: Optional[str] = None

# In-memory storage for request tracking
request_tracker = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Software Development Engine",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    services = {
        "api": "healthy",
        "github": "unknown",
        "llm": "unknown"
    }
    return {
        "status": "healthy",
        "services": services,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api-endpoint", response_model=BuildResponse)
async def handle_build_request(
    request: BuildRequest, 
    background_tasks: BackgroundTasks
):
    # Main endpoint to handle both Round 1: Build and Round 2: Update requests
    
    try:
        # Generate unique request ID for tracking
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"Request {request_id}: Processing round {request.round} for task {request.task}")
        
        # 1. Verify secret
        if not verify_secret(request.secret):
            logger.warning(f"Request {request_id}: Invalid secret")
            raise HTTPException(status_code=401, detail="Invalid secret")
        
        # 2. Store request in tracker
        request_tracker[request_id] = {
            "status": "processing",
            "task": request.task,
            "round": request.round,
            "started_at": datetime.utcnow().isoformat()
        }
        
        # 3. Process in background (to meet 10-minute requirement)
        background_tasks.add_task(
            process_build_request,
            request_id,
            request
        )
        
        return BuildResponse(
            status="accepted",
            message=f"Request {request_id} is being processed. Round {request.round} for task {request.task}",
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_build_request(request_id: str, request: BuildRequest):
    """
    Background task to process the build/update request
    """
    try:
        # Update tracker
        request_tracker[request_id]["status"] = "processing_attachments"
        
        # Handle attachments
        attachment_files = handle_attachments(request.attachments)
        
        if request.round == 1:
            # Round 1: Build new application
            await process_round1_request(request_id, request, attachment_files)
        else:
            # Round 2: Update existing application
            await process_round2_request(request_id, request, attachment_files)
            
        # Mark as completed
        request_tracker[request_id]["status"] = "completed"
        request_tracker[request_id]["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Request {request_id}: Successfully completed")
        
    except Exception as e:
        # Mark as failed
        request_tracker[request_id]["status"] = "failed"
        request_tracker[request_id]["error"] = str(e)
        request_tracker[request_id]["failed_at"] = datetime.utcnow().isoformat()
        
        logger.error(f"Request {request_id}: Failed - {str(e)}")

async def process_round1_request(request_id: str, request: BuildRequest, attachment_files: List[str]):
    """
    Process Round 1 - Build new application
    """
    logger.info(f"Request {request_id}: Starting Round 1 build process")
    
    # 1. Generate application code using LLM
    request_tracker[request_id]["status"] = "generating_code"
    generated_code = generate_application_code(
        brief=request.brief,
        checks=request.checks,
        attachments=attachment_files
    )
    
    # 2. Parse generated code into files
    request_tracker[request_id]["status"] = "parsing_code"
    code_files = parse_code_output(generated_code)
    
    # 3. Create GitHub repository
    request_tracker[request_id]["status"] = "creating_repo"
    repo_name = f"{request.task}-round{request.round}"
    repo_info = create_github_repo(
        repo_name=repo_name,
        code_files=code_files,
        task_id=request.task
    )
    
    # 4. Enable GitHub Pages
    request_tracker[request_id]["status"] = "enabling_pages"
    pages_info = enable_github_pages(repo_info["repo_url"])
    
    # 5. Verify deployment
    request_tracker[request_id]["status"] = "verifying_deployment"
    deployment_success = verify_pages_deployment(pages_info["pages_url"])
    
    if not deployment_success:
        raise Exception("GitHub Pages deployment verification failed")
    
    # 6. Notify evaluation service
    request_tracker[request_id]["status"] = "notifying_evaluation"
    notification_data = EvaluationNotification(
        email=request.email,
        task=request.task,
        round=request.round,
        nonce=request.nonce,
        repo_url=repo_info["repo_url"],
        commit_sha=repo_info["commit_sha"],
        pages_url=pages_info["pages_url"]
    )
    
    await notify_evaluation_service(
        evaluation_url=request.evaluation_url,
        notification_data=notification_data
    )
    
    # Store successful results
    request_tracker[request_id]["repo_url"] = repo_info["repo_url"]
    request_tracker[request_id]["pages_url"] = pages_info["pages_url"]
    request_tracker[request_id]["commit_sha"] = repo_info["commit_sha"]

async def process_round2_request(request_id: str, request: BuildRequest, attachment_files: List[str]):
    """
    Process Round 2 - Update existing application
    """
    logger.info(f"Request {request_id}: Starting Round 2 update process")
    
    # 1. Generate updated code using LLM
    request_tracker[request_id]["status"] = "generating_updates"
    updated_code = generate_application_code(
        brief=request.brief,
        checks=request.checks,
        attachments=attachment_files,
        is_update=True
    )
    
    # 2. Parse updated code
    request_tracker[request_id]["status"] = "parsing_updates"
    updated_files = parse_code_output(updated_code)
    
    # 3. Update GitHub repository (use repo from round 1)
    request_tracker[request_id]["status"] = "updating_repo"
    repo_name = f"{request.task}-round1"  # Use original repo from round 1
    repo_info = update_github_repo(
        repo_name=repo_name,
        updated_files=updated_files,
        commit_message=f"Round {request.round} updates"
    )
    
    # 4. Verify redeployment
    request_tracker[request_id]["status"] = "verifying_redeployment"
    pages_url = f"https://{os.getenv('GITHUB_USERNAME')}.github.io/{repo_name}/"
    deployment_success = verify_pages_deployment(pages_url)
    
    if not deployment_success:
        raise Exception("GitHub Pages redeployment verification failed")
    
    # 5. Notify evaluation service
    request_tracker[request_id]["status"] = "notifying_evaluation"
    notification_data = EvaluationNotification(
        email=request.email,
        task=request.task,
        round=request.round,
        nonce=request.nonce,
        repo_url=repo_info["repo_url"],
        commit_sha=repo_info["commit_sha"],
        pages_url=pages_url
    )
    
    await notify_evaluation_service(
        evaluation_url=request.evaluation_url,
        notification_data=notification_data
    )
    
    # storing successful results
    request_tracker[request_id]["repo_url"] = repo_info["repo_url"]
    request_tracker[request_id]["pages_url"] = pages_url
    request_tracker[request_id]["commit_sha"] = repo_info["commit_sha"]

@app.get("/status/{request_id}")
async def get_request_status(request_id: str):
    """
    Check status of a build request
    """
    if request_id not in request_tracker:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    return request_tracker[request_id]

@app.get("/requests")
async def list_requests(limit: int = 10):
    """
    List recent requests (for monitoring)
    """
    # sort by started_at timestamp
    sorted_requests = sorted(
        request_tracker.items(),
        key=lambda x: x[1].get('started_at', ''),
        reverse=True
    )[:limit]
    
    return {
        "total_requests": len(request_tracker),
        "recent_requests": dict(sorted_requests)
    }

# Error handlers
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # environment variables' check
    required_env_vars = ["GITHUB_TOKEN", "GEMINI_API_KEY", "STUDENT_SECRET", "GITHUB_USERNAME"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )