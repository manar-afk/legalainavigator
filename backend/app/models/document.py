from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class DocumentMeta(BaseModel):
    """Metadata for an uploaded or ingested document."""
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str = "text/plain"
    file_size_bytes: int = 0
    total_pages: Optional[int] = Field(
        default=None,
        description="Total page count if the format provides pagination (e.g. PDF). None for flow formats like DOCX or TXT."
    )
    total_paragraphs: Optional[int] = Field(
        default=None,
        description="Total paragraph count if available."
    )
    total_characters: int = 0
    total_chunks: int = 0
    uploaded_at: Optional[str] = None
    hash_sha256: Optional[str] = None
    has_injection_flags: bool = False
    injection_warnings: List[str] = Field(default_factory=list)


class DocumentSpan(BaseModel):
    """Precise coordinates and source references in the original document."""
    start_char: int
    end_char: int
    page_number: Optional[int] = Field(
        default=None,
        description="1-indexed page number if pagination is known (e.g. PDF). None for unpaginated DOCX/TXT."
    )
    paragraph_index: Optional[int] = Field(
        default=None,
        description="0-indexed paragraph number if structural paragraphs are tracked (e.g. DOCX)."
    )
    section_number: Optional[str] = None
    section_title: Optional[str] = None


class DocumentChunk(BaseModel):
    """A structurally parsed segment of a legal document preserving section hierarchy."""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    filename: str
    page_number: Optional[int] = None  # None when pagination is unavailable
    paragraph_index: Optional[int] = None
    section_number: Optional[str] = None  # e.g., "8.1", "Clause 4(b)", "SECTION 3"
    section_title: Optional[str] = None   # e.g., "Termination and Notice Period"
    text: str
    span: DocumentSpan
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceSource(BaseModel):
    """Source provenance tracking for evidence."""
    source_type: str = "user_document"  # "user_document", "statute", "regulation"
    title: str
    section_reference: Optional[str] = None
    page_number: Optional[int] = None
    quote: str
    confidence_score: float = 1.0
    effective_date: Optional[str] = None
    last_amended: Optional[str] = None
    is_authoritative: bool = True
