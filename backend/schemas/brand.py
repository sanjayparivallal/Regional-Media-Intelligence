"""
Brand-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel


class BrandAliasCreate(BaseModel):
    alias: str
    alias_type: str = "name"  # name, abbreviation, misspelling, regional


class BrandAliasResponse(BaseModel):
    id: UUID
    alias: str
    alias_type: str

    class Config:
        from_attributes = True


class BrandCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = []
    fuzzy_threshold: float = 0.85
    aliases: List[BrandAliasCreate] = []


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    keywords: Optional[List[str]] = None
    fuzzy_threshold: Optional[float] = None


class BrandResponse(BaseModel):
    id: UUID
    name: str
    display_name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    active: bool = True
    keywords: list = []
    fuzzy_threshold: float = 0.85
    total_mentions: int = 0
    critical_alerts: int = 0
    last_mention_at: Optional[datetime] = None
    aliases: List[BrandAliasResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
