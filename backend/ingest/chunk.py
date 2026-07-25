import re
from dataclasses import dataclass, field

import tiktoken

MAX_CHUNK_TOKENS = 500

_encoding = tiktoken.get_encoding("cl100k_base")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    heading_path: list[str]
    text: str
    token_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.token_count = count_tokens(self.text)


def count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


def chunk_markdown(markdown: str, max_tokens: int = MAX_CHUNK_TOKENS) -> list[Chunk]:
    """Splits Markdown into chunks along heading and paragraph boundaries.

    Each chunk keeps the titles of its ancestor headings (heading_path). A single
    paragraph larger than max_tokens is kept whole rather than split mid-sentence —
    revisit if real documents turn out to have very deeply nested, long sections.
    """
    heading_stack: list[tuple[int, str]] = []
    chunks: list[Chunk] = []
    current_paragraphs: list[str] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current_paragraphs, current_tokens
        text = "\n\n".join(current_paragraphs).strip()
        if text:
            chunks.append(Chunk(heading_path=[title for _, title in heading_stack], text=text))
        current_paragraphs = []
        current_tokens = 0

    for block in re.split(r"\n\s*\n", markdown):
        block = block.strip()
        if not block:
            continue

        heading_match = _HEADING_RE.match(block)
        if heading_match:
            flush()
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            heading_stack[:] = [h for h in heading_stack if h[0] < level]
            heading_stack.append((level, title))
            continue

        block_tokens = count_tokens(block)
        if current_paragraphs and current_tokens + block_tokens > max_tokens:
            flush()

        current_paragraphs.append(block)
        current_tokens += block_tokens

    flush()
    return chunks
