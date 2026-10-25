"""Extract text without discarding source page numbers."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfProcessingError(ValueError):
    """A PDF is unsupported, damaged or does not contain extractable text."""


@dataclass(frozen=True)
class Page:
    number: int  # Human-readable, 1-based PDF page number.
    text: str


@dataclass(frozen=True)
class Chunk:
    page_number: int
    chunk_index: int  # 0-based within its page.
    text: str


def extract_pages(pdf_bytes: bytes) -> list[Page]:
    """Keep the page boundary; reject encrypted and image-only documents.

    Blank pages in an otherwise text-based document are allowed and simply
    produce no chunks. OCR is deliberately not included in E1.
    """
    if not pdf_bytes.lstrip().startswith(b"%PDF-"):
        raise PdfProcessingError("Dosya geçerli bir PDF başlığı içermiyor.")
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
        if reader.is_encrypted:
            raise PdfProcessingError("Şifreli PDF dosyaları desteklenmiyor.")
        pages = [
            Page(number=i, text=re.sub(r"\s+", " ", page.extract_text() or "").strip())
            for i, page in enumerate(reader.pages, start=1)
        ]
    except PdfProcessingError:
        raise
    except (PdfReadError, ValueError, TypeError, KeyError, OSError, IndexError) as exc:
        raise PdfProcessingError("PDF okunamadı veya bozuk.") from exc
    if not pages or not any(page.text for page in pages):
        raise PdfProcessingError("PDF'de okunabilir metin yok (taranmış PDF için OCR kapsam dışı).")
    return pages


def chunk_pages(pages: list[Page], *, words_per_chunk: int = 450, overlap: int = 50) -> list[Chunk]:
    """Word chunks never cross a PDF page boundary."""
    if words_per_chunk <= 0 or overlap < 0 or overlap >= words_per_chunk:
        raise ValueError("words_per_chunk pozitif; overlap daha küçük ve negatif olmayan bir sayı olmalı.")
    result: list[Chunk] = []
    for page in pages:
        words = page.text.split()
        step = words_per_chunk - overlap
        for index, start in enumerate(range(0, len(words), step)):
            segment = words[start : start + words_per_chunk]
            if segment:
                result.append(Chunk(page_number=page.number, chunk_index=index, text=" ".join(segment)))
            if start + words_per_chunk >= len(words):
                break
    return result
