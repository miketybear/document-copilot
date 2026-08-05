from pydantic_ai.tools import ToolDefinition

from app.mcp.toolsets import _not_disabled


def test_not_disabled_excludes_disabled_tool_names():
    predicate = _not_disabled({"delete_work_order"})

    assert predicate(None, ToolDefinition(name="search_work_orders")) is True
    assert predicate(None, ToolDefinition(name="delete_work_order")) is False


def test_not_disabled_with_empty_set_excludes_nothing():
    predicate = _not_disabled(set())

    assert predicate(None, ToolDefinition(name="anything")) is True
