import os
import time
import requests
from github import Github, GithubException
import logging

logger = logging.getLogger(__name__)

def enable_github_pages(repo_url: str) -> Dict:
    """
    Enable GitHub Pages for a repository
    """
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
        
        # Extract repo name from URL
        repo_name = extract_repo_name_from_url(repo_url)
        user = g.get_user()
        repo = user.get_repo(repo_name)
        
        # Enable GitHub Pages
        pages = repo.get_pages()
        if not pages:
            # If pages doesn't exist, create it
            repo.create_pages_site(
                source={
                    "branch": "main",
                    "path": "/"
                }
            )
            logger.info(f"Enabled GitHub Pages for {repo_name}")
        else:
            logger.info(f"GitHub Pages already enabled for {repo_name}")
        
        # Build pages URL
        github_username = os.getenv("GITHUB_USERNAME")
        pages_url = f"https://{github_username}.github.io/{repo_name}/"
        
        return {
            "pages_url": pages_url,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to enable GitHub Pages: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "pages_url": None
        }

def verify_pages_deployment(pages_url: str, max_attempts: int = 10) -> bool:
    """
    Verify that GitHub Pages is deployed and accessible
    """
    for attempt in range(max_attempts):
        try:
            response = requests.get(pages_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"GitHub Pages deployment verified: {pages_url}")
                return True
            else:
                logger.warning(f"Pages not ready yet (attempt {attempt + 1}): HTTP {response.status_code}")
                
        except requests.RequestException as e:
            logger.warning(f"Pages not accessible yet (attempt {attempt + 1}): {str(e)}")
        
        # Wait before retrying
        time.sleep(30)  # Wait 30 seconds between checks
    
    logger.error(f"GitHub Pages deployment failed after {max_attempts} attempts")
    return False

def extract_repo_name_from_url(repo_url: str) -> str:
    """
    Extract repository name from GitHub URL
    """
    # Handle both https://github.com/username/repo and https://github.com/username/repo/
    repo_url = repo_url.rstrip('/')
    return repo_url.split('/')[-1]