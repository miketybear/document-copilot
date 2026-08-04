from pydantic_ai.messages import ModelMessage, ToolReturnPart

from app.mcp.toolsets import MCPToolsetBundle, humanize_tool_name


def extract_tool_source_citations(messages: list[ModelMessage], bundle: MCPToolsetBundle) -> list[dict]:
    """One citation per MCP tool call this turn, labeling which external system/record type it
    came from (e.g. {"system": "Maximo", "record_type": "Work Orders"}). Unlike document
    citations, these aren't grounding-checked — they're a record of what was consulted, not a
    claim the model has to justify per passage."""
    citations: list[dict] = []
    for message in messages:
        for part in getattr(message, "parts", []):
            if not isinstance(part, ToolReturnPart):
                continue
            citation = _citation_for_tool(part.tool_name, bundle)
            if citation is not None:
                citations.append(citation)
    return citations


def _citation_for_tool(tool_name: str, bundle: MCPToolsetBundle) -> dict | None:
    for prefix, connection_name in bundle.connection_name_by_prefix.items():
        marker = f"{prefix}_"
        if tool_name.startswith(marker):
            unprefixed = tool_name[len(marker) :]
            return {
                "system": connection_name,
                "record_type": humanize_tool_name(unprefixed),
                "tool_name": unprefixed,
            }
    return None
