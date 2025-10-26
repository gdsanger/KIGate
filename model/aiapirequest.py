from pydantic import BaseModel
from typing import Optional

class aiapirequest(BaseModel):
    job_id: str
    user_id: str
    model: str    
    message: Optional[str] = None
    role: Optional[str] = None
    prompt: Optional[str] = None
    
