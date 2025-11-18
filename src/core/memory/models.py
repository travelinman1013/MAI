from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
