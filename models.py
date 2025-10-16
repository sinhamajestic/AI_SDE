from pydantic import BaseModel
from typing import List, Optional

class Attachment(BaseModel):
    name: str
    url: str

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