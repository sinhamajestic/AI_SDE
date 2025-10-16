import os
import time
import requests
from github import Github, GithubException
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class GithubService:
    def __init__(self):
        self.github = Github(os.getenv("GITHUB_TOKEN"))
        self.user = self.github.get_user()

    def create_repo(self, repo_name: str, code_files: List[Dict], task_id: str) -> Dict:
        try:
            repo = self.user.create_repo(
                name=repo_name,
                description=f"Auto-generated app for task: {task_id}",
                auto_init=False,
                private=False
            )
            logger.info(f"Created repository: {repo.html_url}")

    
            commit_sha = self._commit_files(repo, code_files, "Add")
            
            return {
                "repo_url": repo.html_url,
                "repo_name": repo_name,
                "commit_sha": commit_sha,
                "success": True
            }
        except Exception as e:
            logger.error(f"Failed to create GitHub repository: {str(e)}")
            return {"success": False, "error": str(e)}

    def update_repo(self, repo_name: str, updated_files: List[Dict], commit_message: str) -> Dict:
        try:
            repo = self.user.get_repo(repo_name)
            commit_sha = self._commit_files(repo, updated_files, commit_message, is_update=True)
            return {
                "repo_url": repo.html_url,
                "repo_name": repo_name,
                "commit_sha": commit_sha,
                "success": True
            }
        except Exception as e:
            logger.error(f"Failed to update GitHub repository: {str(e)}")
            return {"success": False, "error": str(e)}

    def enable_pages(self, repo_url: str) -> Dict:
        try:
            repo_name = self._extract_repo_name_from_url(repo_url)
            repo = self.user.get_repo(repo_name)

            headers = {
                "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
                "Accept": "application/vnd.github.v3+json",
            }
            source = {"branch": "main", "path": "/"}
            response = requests.post(
                f"https://api.github.com/repos/{self.user.login}/{repo_name}/pages",
                headers=headers,
                json={"source": source},
            )
            response.raise_for_status()  # This will raise an error if the request fails
            
            logger.info(f"Enabled GitHub Pages for {repo_name}")
            
            pages_url = f"https://{os.getenv('GITHUB_USERNAME')}.github.io/{repo_name}/"
            return {"pages_url": pages_url, "success": True}
        except Exception as e:
            logger.error(f"Failed to enable GitHub Pages: {str(e)}")
            return {"success": False, "error": str(e), "pages_url": None}

    def verify_deployment(self, pages_url: str, max_attempts: int = 10):
        for attempt in range(max_attempts):
            try:
                response = requests.get(pages_url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"GitHub Pages deployment verified: {pages_url}")
                    return
            except requests.RequestException as e:
                logger.warning(f"Pages not accessible yet (attempt {attempt + 1}): {str(e)}")
            time.sleep(30)
        raise Exception("GitHub Pages deployment verification failed")

    def _commit_files(self, repo, files: List[Dict], message_prefix: str, is_update: bool = False) -> str:
        commit_sha = None
        for file_info in files:
            file_path = file_info["path"]
            file_content = file_info["content"]
            try:
                if is_update:
                    contents = repo.get_contents(file_path)
                    result = repo.update_file(file_path, f"Update {file_path}", file_content, contents.sha)
                else:
                    result = repo.create_file(file_path, f"{message_prefix} {file_path}", file_content)
                commit_sha = result["commit"].sha
                logger.info(f"Committed file: {file_path}")
            except GithubException as e:
                if e.status == 404 and is_update:
                    result = repo.create_file(file_path, f"Add {file_path}", file_content)
                    commit_sha = result["commit"].sha
                else:
                    raise e
        return commit_sha

    def _create_mit_license(self) -> str:
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

    def _extract_repo_name_from_url(self, repo_url: str) -> str:
        return repo_url.rstrip('/').split('/')[-1]