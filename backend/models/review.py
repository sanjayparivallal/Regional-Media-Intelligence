import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Review(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str
    entity_type: str
    issue_type: str
    reason: Optional[str] = None
    original_value: Optional[Dict[str, Any]] = None
    corrected_value: Optional[Dict[str, Any]] = None
    status: str = "pending"
    reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None

class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: Optional[str] = None
    article_id: Optional[str] = None
    action: str
    component: str
    status: str = "success"
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
