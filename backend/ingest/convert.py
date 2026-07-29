import html
from pathlib import Path

from docling.document_converter import DocumentConverter

# A single converter instance reuses its (expensive to load) OCR/layout models across files.
_converter = DocumentConverter()


def convert_to_markdown(path: Path) -> str:
    """Converts a PDF/DOCX/PPTX file to normalized Markdown.

    OCR runs automatically per-page for PDFs that lack a text layer (docling's default
    PdfPipelineOptions.do_ocr=True, force_full_page_ocr=False) — no extra config needed.
    """
    result = _converter.convert(str(path))
    markdown = result.document.export_to_markdown()
    # docling's markdown serializer HTML-escapes text content (e.g. "->" from OCR'd
    # scans comes out as "-&gt;"); unescape here so both content_markdown and chunk_text
    # store readable text rather than entities.
    return html.unescape(markdown)
