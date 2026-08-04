from pydantic_ai.messages import ToolReturnPart

from app.mcp.citations import extract_tool_source_citations
from app.mcp.toolsets import MCPToolsetBundle, humanize_tool_name


class FakeMessage:
    def __init__(self, parts):
        self.parts = parts


def test_extract_tool_source_citations_labels_by_connection_prefix():
    bundle = MCPToolsetBundle(toolsets=[], connection_name_by_prefix={"maximo": "Maximo"})
    messages = [FakeMessage([ToolReturnPart(tool_name="maximo_search_work_orders", content=[])])]

    citations = extract_tool_source_citations(messages, bundle)

    assert citations == [{"system": "Maximo", "record_type": "Work Orders", "tool_name": "search_work_orders"}]


def test_extract_tool_source_citations_ignores_non_mcp_tools():
    bundle = MCPToolsetBundle(toolsets=[], connection_name_by_prefix={"maximo": "Maximo"})
    messages = [FakeMessage([ToolReturnPart(tool_name="search_documents", content=[])])]

    assert extract_tool_source_citations(messages, bundle) == []


def test_extract_tool_source_citations_ignores_non_tool_return_parts():
    bundle = MCPToolsetBundle(toolsets=[], connection_name_by_prefix={"maximo": "Maximo"})
    messages = [FakeMessage([object()])]

    assert extract_tool_source_citations(messages, bundle) == []


def test_humanize_tool_name_strips_verb_and_title_cases():
    assert humanize_tool_name("search_work_orders") == "Work Orders"
    assert humanize_tool_name("get_purchase_order") == "Purchase Order"
    assert humanize_tool_name("convert_to_usd") == "Convert To Usd"
