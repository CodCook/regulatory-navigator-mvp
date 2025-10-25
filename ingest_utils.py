from typing import List
import io

# Lightweight parsers for demo MVP; robust parsing may require additional libs/services.

def _safe_text(s):
    try:
        return s if isinstance(s, str) else s.decode('utf-8', errors='ignore')
    except Exception:
        return ''


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return ''
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        parts: List[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or '')
            except Exception:
                continue
        return '\n'.join(parts)
    except Exception:
        return ''


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        import docx  # python-docx
    except Exception:
        return ''
    try:
        f = io.BytesIO(file_bytes)
        document = docx.Document(f)
        parts = [p.text for p in document.paragraphs if p.text]
        return '\n'.join(parts)
    except Exception:
        return ''


def extract_text_from_txt(file_bytes: bytes) -> str:
    return _safe_text(file_bytes)


def extract_text_from_files(named_files: List[tuple]) -> str:
    """
    named_files: list of tuples (filename, bytes)
    Returns concatenated text.
    """
    blobs: List[str] = []
    for name, data in named_files:
        lower = (name or '').lower()
        text = ''
        if lower.endswith('.pdf'):
            text = extract_text_from_pdf(data)
        elif lower.endswith('.docx'):
            text = extract_text_from_docx(data)
        elif lower.endswith('.txt'):
            text = extract_text_from_txt(data)
        else:
            # attempt utf-8 decode fallback
            text = extract_text_from_txt(data)
        if text:
            blobs.append(text)
    return '\n\n'.join(blobs)
