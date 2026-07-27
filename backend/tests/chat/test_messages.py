from app.chat.messages import MAX_TITLE_LENGTH, derive_title


def test_strips_leading_english_question_phrase():
    assert derive_title("How do I maintain a safety level transmitter?") == "Maintain a safety level transmitter"


def test_strips_contracted_leading_phrase():
    assert derive_title("What's the maternity leave policy?") == "Maternity leave policy"


def test_strips_trailing_vietnamese_question_phrase():
    assert derive_title("Chính sách nghỉ thai sản là gì?") == "Chính sách nghỉ thai sản"


def test_passes_through_text_with_no_known_question_phrase():
    assert derive_title("Safety level transmitter maintenance") == "Safety level transmitter maintenance"


def test_truncates_long_titles_with_ellipsis():
    long_text = "What is the process for requesting emergency leave when a family member is hospitalized unexpectedly?"

    title = derive_title(long_text)

    assert len(title) == MAX_TITLE_LENGTH + 1
    assert title.endswith("…")
