import os
import base64
from github import Github, GithubException
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def create_github_repo(repo_name: str, code_files: List[Dict], task_id: str) -> Dict:
    """
    Create a new GitHub repository and commit all code files
    """
    try:
        # Initialize GitHub client
        g = Github(os.getenv("GITHUB_TOKEN"))
        user = g.get_user()
        
        # Create repository
        repo_description = f"Auto-generated app for task: {task_id}"
        repo = user.create_repo(
            name=repo_name,
            description=repo_description,
            auto_init=False,
            private=False
        )
        
        logger.info(f"Created repository: {repo.html_url}")
        
        # Create MIT LICENSE
        license_content = create_mit_license()
        repo.create_file("LICENSE", "Add MIT License", license_content)
        
        # Create all code files
        commit_sha = None
        for file_info in code_files:
            try:
                file_path = file_info["path"]
                file_content = file_info["content"]
                
                # Create file in repository
                result = repo.create_file(file_path, f"Add {file_path}", file_content)
                commit_sha = result["commit"].sha
                logger.info(f"Created file: {file_path}")
                
            except GithubException as e:
                if e.status == 409:  # File already exists
                    logger.warning(f"File {file_path} already exists, updating...")
                    # Get existing file and update it
                    contents = repo.get_contents(file_path)
                    result = repo.update_file(
                        file_path, 
                        f"Update {file_path}", 
                        file_content, 
                        contents.sha
                    )
                    commit_sha = result["commit"].sha
                else:
                    raise e
        
        return {
            "repo_url": repo.html_url,
            "repo_name": repo_name,
            "commit_sha": commit_sha,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to create GitHub repository: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def update_github_repo(repo_name: str, updated_files: List[Dict], commit_message: str) -> Dict:
    """
    Update an existing GitHub repository with new files
    """
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
        user = g.get_user()
        
        # Get existing repository
        repo = user.get_repo(repo_name)
        
        commit_sha = None
        for file_info in updated_files:
            file_path = file_info["path"]
            new_content = file_info["content"]
            
            try:
                # Try to get existing file to update it
                existing_file = repo.get_contents(file_path)
                result = repo.update_file(
                    file_path,
                    commit_message,
                    new_content,
                    existing_file.sha
                )
                commit_sha = result["commit"].sha
                logger.info(f"Updated file: {file_path}")
                
            except GithubException as e:
                if e.status == 404:  # File doesn't exist, create it
                    result = repo.create_file(file_path, commit_message, new_content)
                    commit_sha = result["commit"].sha
                    logger.info(f"Created new file: {file_path}")
                else:
                    raise e
        
        return {
            "repo_url": repo.html_url,
            "repo_name": repo_name,
            "commit_sha": commit_sha,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to update GitHub repository: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def create_mit_license() -> str:
    """
    Create MIT License content
    """
    current_year = datetime.now().year
    github_username = os.getenv("GITHUB_USERNAME", "student")
    
    return f"""MIT License

Copyright (c) {current_year} {github_username}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""