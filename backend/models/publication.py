import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Publication(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    language: Optional[str] = None
    region: Optional[str] = None
    circulation: int = 0
    tier: int = 1
    publisher: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
