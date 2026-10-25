import pytest
from pypdf import PdfWriter
from io import BytesIO

from coursegraph.pdf_processing import Page, PdfProcessingError, chunk_pages, extract_pages


def test_two_page_pdf_text_keeps_page_numbers(sample_pdf):
    pages = extract_pages(sample_pdf)
    assert [p.number for p in pages] == [1, 2]
    assert "First page" in pages[0].text
    assert "Second page" in pages[1].text


def test_chunks_never_cross_page_boundaries():
    pages = [Page(1, "a b c d e"), Page(2, "f g h i j")]
    chunks = chunk_pages(pages, words_per_chunk=3, overlap=1)
    assert [(c.page_number, c.text) for c in chunks] == [
        (1, "a b c"), (1, "c d e"), (2, "f g h"), (2, "h i j")
    ]
    assert [c.chunk_index for c in chunks] == [0, 1, 0, 1]


def test_blank_pdf_rejected():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buffer = BytesIO()
    writer.write(buffer)
    with pytest.raises(PdfProcessingError, match="okunabilir metin"):
        extract_pages(buffer.getvalue())


def test_non_pdf_rejected():
    with pytest.raises(PdfProcessingError):
        extract_pages(b"bad data")


def test_invalid_chunk_settings_rejected():
    with pytest.raises(ValueError):
        chunk_pages([Page(1, "text")], words_per_chunk=3, overlap=3)
