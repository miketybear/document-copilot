from pathlib import Path
from unittest.mock import MagicMock

from ingest import convert


def test_convert_to_markdown_unescapes_html_entities(monkeypatch):
    """docling's markdown serializer HTML-escapes OCR'd text (e.g. "->" becomes "-&gt;");
    convert_to_markdown must decode entities before the text is persisted or chunked."""
    result = MagicMock()
    result.document.export_to_markdown.return_value = (
        "go to 1 device setup -&gt; 2 diag/Service &amp; confirm"
    )
    monkeypatch.setattr(convert._converter, "convert", lambda _path: result)

    markdown = convert.convert_to_markdown(Path("dummy.pdf"))

    assert markdown == "go to 1 device setup -> 2 diag/Service & confirm"
    assert "&gt;" not in markdown
    assert "&amp;" not in markdown
