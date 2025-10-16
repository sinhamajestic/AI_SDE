from fastapi import FastAPI, HTTPException, BackgroundTasks
import os
import logging
import uuid
from datetime import datetime

# Import models from the new models.py file
from models import BuildRequest, BuildResponse
from services.build_service import process_build_request
from utils.secret_verifier import verify_secret

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

@app.post("/api-endpoint", response_model=BuildResponse)
async def handle_build_request(
    request: BuildRequest,
    background_tasks: BackgroundTasks
):
    try:
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"Request {request_id}: Processing round {request.round} for task {request.task}")

        if not verify_secret(request.secret):
            logger.warning(f"Request {request_id}: Invalid secret")
            raise HTTPException(status_code=401, detail="Invalid secret")

        request_tracker[request_id] = {
            "status": "processing",
            "task": request.task,
            "round": request.round,
            "started_at": datetime.utcnow().isoformat()
        }

        background_tasks.add_task(
            process_build_request,
            request_id,
            request,
            request_tracker
        )

        return BuildResponse(
            status="accepted",
            message=f"Request {request_id} is being processed. Round {request.round} for task {request.task}",
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{request_id}")
async def get_request_status(request_id: str):
    if request_id not in request_tracker:
        raise HTTPException(status_code=404, detail="Request ID not found")
    return request_tracker[request_id]

if __name__ == "__main__":
    import uvicorn

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