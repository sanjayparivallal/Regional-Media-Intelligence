import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import enum

class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

class DocumentType(str, enum.Enum):
    PDF_SCANNED = "pdf_scanned"
    PDF_TEXT = "pdf_text"
    PDF_MIXED = "pdf_mixed"
    IMAGE = "image"

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    document_type: Optional[DocumentType] = None
    page_count: int = 0
    status: DocumentStatus = DocumentStatus.UPLOADED
    error_message: Optional[str] = None
    publication_id: Optional[str] = None
    publication_date: Optional[datetime] = None
    edition: Optional[str] = None
    source_region: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None
    is_demo: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Page(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page_number: int
    image_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    dpi: int = 300
    has_text_layer: bool = False
    ocr_engine_used: Optional[str] = None
    ocr_language: Optional[str] = None
    ocr_raw_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_word_count: Optional[int] = None
    ocr_bounding_boxes: Optional[List[Dict[str, Any]]] = None
    detected_columns: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Article(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    page_id: str
    document_id: str
    headline: Optional[str] = None
    body_text: Optional[str] = None
    bounding_box: Optional[Dict[str, Any]] = None
    detected_language: Optional[str] = None
    detected_script: Optional[str] = None
    language_confidence: Optional[float] = None
    word_count: int = 0
    article_type: str = "NEWS"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessingJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    status: str = "queued"
    current_stage: str = "pending"
    progress_percentage: int = 0
    stage_details: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
