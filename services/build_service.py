import logging
import os
from datetime import datetime
from typing import Dict, Any

# Import the pydantic model from models.py
from models import EvaluationNotification
from generators.code_generator import generate_and_parse_code
from services.github_service import GithubService
from evaluation.notifier import notify_evaluation_service
from utils.attachment_handler import handle_attachments

logger = logging.getLogger(__name__)

async def process_build_request(request_id: str, request: Dict[str, Any], request_tracker: Dict[str, Any]):
    try:
        request_tracker[request_id]["status"] = "processing_attachments"
        attachment_files = handle_attachments(request.attachments)

        if request.round == 1:
            await process_round1_request(request_id, request, attachment_files, request_tracker)
        else:
            await process_round2_request(request_id, request, attachment_files, request_tracker)

        request_tracker[request_id]["status"] = "completed"
        request_tracker[request_id]["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"Request {request_id}: Successfully completed")

    except Exception as e:
        request_tracker[request_id]["status"] = "failed"
        request_tracker[request_id]["error"] = str(e)
        request_tracker[request_id]["failed_at"] = datetime.utcnow().isoformat()
        logger.error(f"Request {request_id}: Failed - {str(e)}")

async def process_round1_request(request_id: str, request: Dict[str, Any], attachment_files: list, request_tracker: Dict[str, Any]):
    logger.info(f"Request {request_id}: Starting Round 1 build process")

    request_tracker[request_id]["status"] = "generating_code"
    code_files = generate_and_parse_code(request.brief, request.checks, attachment_files)

    github_service = GithubService()
    repo_name = f"{request.task}-round{request.round}"

    request_tracker[request_id]["status"] = "creating_repo"
    repo_info = github_service.create_repo(repo_name, code_files, request.task)

    request_tracker[request_id]["status"] = "enabling_pages"
    pages_info = github_service.enable_pages(repo_info["repo_url"])
    github_service.verify_deployment(pages_info["pages_url"])

    await notify_evaluation(request, repo_info, pages_info["pages_url"])

    request_tracker[request_id].update({
        "repo_url": repo_info["repo_url"],
        "pages_url": pages_info["pages_url"],
        "commit_sha": repo_info["commit_sha"],
    })

async def process_round2_request(request_id: str, request: Dict[str, Any], attachment_files: list, request_tracker: Dict[str, Any]):
    logger.info(f"Request {request_id}: Starting Round 2 update process")

    request_tracker[request_id]["status"] = "generating_updates"
    updated_files = generate_and_parse_code(request.brief, request.checks, attachment_files, is_update=True)

    github_service = GithubService()
    repo_name = f"{request.task}-round1"

    request_tracker[request_id]["status"] = "updating_repo"
    repo_info = github_service.update_repo(repo_name, updated_files, f"Round {request.round} updates")
    pages_url = f"https://{os.getenv('GITHUB_USERNAME')}.github.io/{repo_name}/"
    github_service.verify_deployment(pages_url)

    await notify_evaluation(request, repo_info, pages_url)

    request_tracker[request_id].update({
        "repo_url": repo_info["repo_url"],
        "pages_url": pages_url,
        "commit_sha": repo_info["commit_sha"],
    })

async def notify_evaluation(request: Dict[str, Any], repo_info: Dict[str, Any], pages_url: str):
    notification_data = EvaluationNotification(
        email=request.email,
        task=request.task,
        round=request.round,
        nonce=request.nonce,
        repo_url=repo_info["repo_url"],
        commit_sha=repo_info["commit_sha"],
        pages_url=pages_url,
    )
    await notify_evaluation_service(request.evaluation_url, notification_data)