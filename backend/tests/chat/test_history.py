from pydantic_ai.messages import ModelRequest, ModelResponse

from app.chat.history import (
    MAX_HISTORY_TOKENS,
    build_message_history,
    history_token_count,
)
from app.chat.messages import UIMessage, UIMessagePart


def _message(role: str, text: str, msg_id: str = "m") -> UIMessage:
    return UIMessage(id=msg_id, role=role, parts=[UIMessagePart(type="text", text=text)])


def test_empty_history_returns_empty_list():
    assert build_message_history([]) == []


def test_keeps_user_and_assistant_turns_in_order():
    messages = [_message("user", "What is the leave policy?"), _message("assistant", "You get 12 days.")]

    history = build_message_history(messages)

    assert len(history) == 2
    assert isinstance(history[0], ModelRequest)
    assert history[0].parts[0].content == "What is the leave policy?"
    assert isinstance(history[1], ModelResponse)
    assert history[1].parts[0].content == "You get 12 days."


def test_skips_messages_with_no_text_parts():
    messages = [
        _message("user", "What is the leave policy?"),
        UIMessage(id="m2", role="assistant", parts=[UIMessagePart(type="data-citation", text=None)]),
    ]

    history = build_message_history(messages)

    assert len(history) == 1


def test_skips_system_role_messages():
    messages = [_message("system", "You are a helpful assistant."), _message("user", "Hi")]

    history = build_message_history(messages)

    assert len(history) == 1
    assert history[0].parts[0].content == "Hi"


def test_drops_oldest_turns_once_token_budget_is_exceeded():
    # Each turn is ~2000 tokens (500 repeated words), so only the most recent ~3 fit in the budget.
    long_text = "word " * 2000
    messages = [_message("user", long_text, msg_id=f"m{i}") for i in range(6)]

    history = build_message_history(messages)

    assert len(history) < len(messages)
    # the most recent message must be the last one kept
    assert history[-1].parts[0].content == messages[-1].parts[0].text


def test_always_keeps_the_turn_immediately_before_the_current_one_even_if_it_alone_exceeds_budget():
    huge_text = "word " * 20000  # far larger than MAX_HISTORY_TOKENS on its own

    history = build_message_history([_message("user", huge_text)])

    assert len(history) == 1


def test_total_kept_tokens_stay_within_budget_for_many_small_turns():
    messages = [_message("user" if i % 2 == 0 else "assistant", f"turn {i} " * 50) for i in range(40)]

    history = build_message_history(messages)

    assert history_token_count(history) <= MAX_HISTORY_TOKENS


def test_history_token_count_of_empty_history_is_zero():
    assert history_token_count([]) == 0


def test_history_token_count_matches_build_message_history_budget_enforcement():
    huge_text = "word " * 20000

    history = build_message_history([_message("user", huge_text)])

    assert history_token_count(history) > MAX_HISTORY_TOKENS  # the single-turn guarantee overrides the budget
