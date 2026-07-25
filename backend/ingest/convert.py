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
    return result.document.export_to_markdown()
