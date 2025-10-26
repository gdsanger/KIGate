from pydantic import BaseModel
from typing import Optional, Union

class aiapiresult(BaseModel):
    job_id: str
    user_id: str
    content: str
    success: bool
    error_message: Optional[str] = None
