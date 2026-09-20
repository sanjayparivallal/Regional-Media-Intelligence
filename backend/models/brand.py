import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class BrandAlias(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str
    alias: str

class Brand(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    logo_url: Optional[str] = None
    active: bool = True
    aliases: List[BrandAlias] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    fuzzy_threshold: float = 85.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
