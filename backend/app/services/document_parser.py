import re
import hashlib
import io
from typing import List, Tuple, Optional, Dict, Any
from pypdf import PdfReader
import docx

from ..models.document import DocumentMeta, DocumentChunk, DocumentSpan
from ..core.storage import document_store
from .guardrails import guardrail_service

# Regex to detect major legal section / clause headers
SECTION_HEADER_PATTERN = re.compile(
    r"(?m)^(?P<full_header>(?:SECTION|Section|ARTICLE|Article|CLAUSE|Clause|AMENDMENT CLAUSE|Amendment Clause|SCHEDULE|Schedule)\s+(?P<sec_num>[0-9A-Za-z\.\-]+)(?:\s*[:\-\.]\s*(?P<sec_title>[^\n\r]+))?)",
    re.IGNORECASE
)

# Numbered sub-clause pattern (e.g. "8.1 ", "8.2. ", "1.1 ")
SUB_CLAUSE_PATTERN = re.compile(
    r"(?m)^(?P<sub_num>\d+\.\d+)\s+(?P<sub_text>[^\n\r]+)"
)


class LegalDocumentParser:
    """
    Section-aware document parser and chunker that preserves legal hierarchy,
    character/paragraph spans, and format-specific pagination without inventing page numbers.
    """

    @classmethod
    def parse_text_content(
        cls,
        raw_text: str,
        filename: str = "document.txt",
        file_type: str = "text/plain",
        doc_id: Optional[str] = None
    ) -> Tuple[DocumentMeta, List[DocumentChunk]]:
        """
        Parses raw text, performs security inspection, and chunks along section boundaries.
        Page numbers are explicitly None since plain text is unpaginated.
        """
        _, flags = guardrail_service.sanitize_untrusted_document(raw_text)
        raw_bytes = raw_text.encode("utf-8")
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        meta = DocumentMeta(
            doc_id=doc_id or hashlib.md5(f"{filename}_{sha256}".encode()).hexdigest()[:16],
            filename=filename,
            file_type=file_type,
            file_size_bytes=len(raw_bytes),
            total_pages=None,  # No pagination in plain text
            total_characters=len(raw_text),
            hash_sha256=sha256,
            has_injection_flags=len(flags) > 0,
            injection_warnings=flags,
        )

        chunks = cls._chunk_legal_document(raw_text, meta)
        meta.total_chunks = len(chunks)

        # Retain authentic extracted text and raw binary bytes in storage
        document_store.add_document(meta, raw_text, chunks, raw_bytes=raw_bytes)
        return meta, chunks

    @classmethod
    def parse_pdf_bytes(
        cls,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        doc_id: Optional[str] = None
    ) -> Tuple[DocumentMeta, List[DocumentChunk]]:
        """
        Parses PDF bytes with verifiable page tracking.
        """
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)

        page_offsets: List[Tuple[int, int, int]] = []
        full_text_parts = []
        current_offset = 0

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            page_text = page.extract_text() or ""
            start = current_offset
            full_text_parts.append(page_text)
            current_offset += len(page_text)
            end = current_offset
            page_offsets.append((page_num, start, end))

            if page_idx < total_pages - 1:
                full_text_parts.append("\n\n")
                current_offset += 2

        full_text = "".join(full_text_parts)
        _, flags = guardrail_service.sanitize_untrusted_document(full_text)
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        meta = DocumentMeta(
            doc_id=doc_id or hashlib.md5(f"{filename}_{sha256}".encode()).hexdigest()[:16],
            filename=filename,
            file_type="application/pdf",
            file_size_bytes=len(pdf_bytes),
            total_pages=total_pages,  # Known PDF page count
            total_characters=len(full_text),
            hash_sha256=sha256,
            has_injection_flags=len(flags) > 0,
            injection_warnings=flags,
        )

        chunks = cls._chunk_legal_document(full_text, meta, page_offsets=page_offsets)
        meta.total_chunks = len(chunks)

        document_store.add_document(meta, full_text, chunks, raw_bytes=pdf_bytes)
        return meta, chunks

    @classmethod
    def parse_docx_bytes(
        cls,
        docx_bytes: bytes,
        filename: str = "document.docx",
        doc_id: Optional[str] = None
    ) -> Tuple[DocumentMeta, List[DocumentChunk]]:
        """
        Parses DOCX bytes using python-docx.
        Preserves structural paragraph indexes and character spans.
        Does NOT invent page numbers (total_pages=None, chunk page_number=None).
        """
        doc = docx.Document(io.BytesIO(docx_bytes))
        total_paragraphs = len(doc.paragraphs)

        para_parts: List[str] = []
        para_offsets: List[Tuple[int, int, int]] = []  # (para_idx, start_char, end_char)
        current_offset = 0

        for p_idx, p in enumerate(doc.paragraphs):
            p_text = p.text
            start = current_offset
            para_parts.append(p_text)
            current_offset += len(p_text)
            end = current_offset
            para_offsets.append((p_idx, start, end))

            if p_idx < total_paragraphs - 1:
                para_parts.append("\n\n")
                current_offset += 2

        full_text = "".join(para_parts)
        _, flags = guardrail_service.sanitize_untrusted_document(full_text)
        sha256 = hashlib.sha256(docx_bytes).hexdigest()

        meta = DocumentMeta(
            doc_id=doc_id or hashlib.md5(f"{filename}_{sha256}".encode()).hexdigest()[:16],
            filename=filename,
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size_bytes=len(docx_bytes),
            total_pages=None,  # Crucial: Page count is deliberately None for DOCX flow formats
            total_paragraphs=total_paragraphs,
            total_characters=len(full_text),
            hash_sha256=sha256,
            has_injection_flags=len(flags) > 0,
            injection_warnings=flags,
        )

        chunks = cls._chunk_legal_document(full_text, meta, para_offsets=para_offsets)
        meta.total_chunks = len(chunks)

        document_store.add_document(meta, full_text, chunks, raw_bytes=docx_bytes)
        return meta, chunks

    @classmethod
    def _chunk_legal_document(
        cls,
        text: str,
        meta: DocumentMeta,
        page_offsets: Optional[List[Tuple[int, int, int]]] = None,
        para_offsets: Optional[List[Tuple[int, int, int]]] = None,
    ) -> List[DocumentChunk]:
        """
        Splits legal text along structural section boundaries.
        Preserves exact start_char and end_char in text so text[start:end] == chunk.text.
        """
        if not text.strip():
            return []

        chunks: List[DocumentChunk] = []

        def get_page_for_char(char_idx: int) -> Optional[int]:
            if not page_offsets:
                return None
            for page_num, start, end in page_offsets:
                if start <= char_idx <= end:
                    return page_num
            return None

        def get_para_for_char(char_idx: int) -> Optional[int]:
            if not para_offsets:
                return None
            for p_idx, start, end in para_offsets:
                if start <= char_idx <= end:
                    return p_idx
            return None

        # Find all major section headers
        matches = list(SECTION_HEADER_PATTERN.finditer(text))

        # If no explicit sections found, split by double newlines
        if not matches:
            paragraphs = list(re.finditer(r"(?:\r?\n\s*){2,}", text))
            if not paragraphs:
                span = DocumentSpan(
                    start_char=0,
                    end_char=len(text),
                    page_number=get_page_for_char(0),
                    paragraph_index=get_para_for_char(0)
                )
                return [DocumentChunk(
                    doc_id=meta.doc_id,
                    filename=meta.filename,
                    page_number=span.page_number,
                    paragraph_index=span.paragraph_index,
                    text=text,
                    span=span
                )]

            last_pos = 0
            for p in paragraphs:
                p_text = text[last_pos:p.start()]
                if p_text.strip():
                    span = DocumentSpan(
                        start_char=last_pos,
                        end_char=p.start(),
                        page_number=get_page_for_char(last_pos),
                        paragraph_index=get_para_for_char(last_pos)
                    )
                    chunks.append(DocumentChunk(
                        doc_id=meta.doc_id,
                        filename=meta.filename,
                        page_number=span.page_number,
                        paragraph_index=span.paragraph_index,
                        text=p_text,
                        span=span
                    ))
                last_pos = p.end()

            if last_pos < len(text) and text[last_pos:].strip():
                span = DocumentSpan(
                    start_char=last_pos,
                    end_char=len(text),
                    page_number=get_page_for_char(last_pos),
                    paragraph_index=get_para_for_char(last_pos)
                )
                chunks.append(DocumentChunk(
                    doc_id=meta.doc_id,
                    filename=meta.filename,
                    page_number=span.page_number,
                    paragraph_index=span.paragraph_index,
                    text=text[last_pos:],
                    span=span
                ))
            return chunks

        # Handle preamble/recitals before the first section
        first_match = matches[0]
        if first_match.start() > 0:
            preamble_text = text[0:first_match.start()]
            if preamble_text.strip():
                span = DocumentSpan(
                    start_char=0,
                    end_char=first_match.start(),
                    page_number=get_page_for_char(0),
                    paragraph_index=get_para_for_char(0),
                    section_number="PREAMBLE",
                    section_title="Preamble & Recitals"
                )
                chunks.append(DocumentChunk(
                    doc_id=meta.doc_id,
                    filename=meta.filename,
                    page_number=span.page_number,
                    paragraph_index=span.paragraph_index,
                    section_number=span.section_number,
                    section_title=span.section_title,
                    text=preamble_text,
                    span=span,
                    metadata={"is_preamble": True}
                ))

        # Process each section
        for i, match in enumerate(matches):
            sec_start = match.start()
            sec_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sec_text = text[sec_start:sec_end]

            sec_num = match.group("sec_num").strip() if match.group("sec_num") else None
            sec_title = match.group("sec_title").strip() if match.group("sec_title") else None

            # Sub-chunk by numbered sub-clauses if long (>800 chars)
            sub_matches = list(SUB_CLAUSE_PATTERN.finditer(sec_text))
            if len(sub_matches) > 1 and len(sec_text) > 800:
                for s_idx, s_m in enumerate(sub_matches):
                    # Text before first sub-clause
                    if s_idx == 0 and s_m.start() > 0:
                        header_block = sec_text[0:s_m.start()]
                        if header_block.strip():
                            sub_span = DocumentSpan(
                                start_char=sec_start,
                                end_char=sec_start + s_m.start(),
                                page_number=get_page_for_char(sec_start),
                                paragraph_index=get_para_for_char(sec_start),
                                section_number=sec_num,
                                section_title=sec_title
                            )
                            chunks.append(DocumentChunk(
                                doc_id=meta.doc_id,
                                filename=meta.filename,
                                page_number=sub_span.page_number,
                                paragraph_index=sub_span.paragraph_index,
                                section_number=sec_num,
                                section_title=sec_title,
                                text=header_block,
                                span=sub_span
                            ))

                    sub_start_in_sec = s_m.start()
                    sub_end_in_sec = sub_matches[s_idx + 1].start() if s_idx + 1 < len(sub_matches) else len(sec_text)
                    sub_text = sec_text[sub_start_in_sec:sub_end_in_sec]
                    sub_num = s_m.group("sub_num")

                    abs_start = sec_start + sub_start_in_sec
                    abs_end = sec_start + sub_end_in_sec
                    sub_span = DocumentSpan(
                        start_char=abs_start,
                        end_char=abs_end,
                        page_number=get_page_for_char(abs_start),
                        paragraph_index=get_para_for_char(abs_start),
                        section_number=f"{sec_num}.{sub_num}" if sec_num and not sub_num.startswith(sec_num) else sub_num,
                        section_title=sec_title
                    )
                    chunks.append(DocumentChunk(
                        doc_id=meta.doc_id,
                        filename=meta.filename,
                        page_number=sub_span.page_number,
                        paragraph_index=sub_span.paragraph_index,
                        section_number=sub_span.section_number,
                        section_title=sec_title,
                        text=sub_text,
                        span=sub_span,
                        metadata={"parent_section": sec_num}
                    ))
            else:
                span = DocumentSpan(
                    start_char=sec_start,
                    end_char=sec_end,
                    page_number=get_page_for_char(sec_start),
                    paragraph_index=get_para_for_char(sec_start),
                    section_number=sec_num,
                    section_title=sec_title
                )
                chunks.append(DocumentChunk(
                    doc_id=meta.doc_id,
                    filename=meta.filename,
                    page_number=span.page_number,
                    paragraph_index=span.paragraph_index,
                    section_number=sec_num,
                    section_title=sec_title,
                    text=sec_text,
                    span=span
                ))

        return chunks


document_parser = LegalDocumentParser()
