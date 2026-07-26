from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.config import settings
from app.retrieval import retriever
from app.retrieval.types import SourcePassage

_INSTRUCTIONS = (Path(__file__).parent / "instructions.md").read_text(encoding="utf-8")

_provider = AzureProvider(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version,
)
_model = OpenAIChatModel(settings.azure_openai_chat_deployment, provider=_provider)

agent = Agent(_model, deps_type=DocumentAgentDeps, output_type=GroundedAnswer, instructions=_INSTRUCTIONS)


@agent.tool
async def search_documents(ctx: RunContext[DocumentAgentDeps], query: str) -> list[SourcePassage]:
    """Search the internal document corpus for passages relevant to the query."""
    return await retriever.search_documents(ctx.deps.supabase_client, query)


@agent.tool
async def read_chunk(ctx: RunContext[DocumentAgentDeps], chunk_id: str) -> SourcePassage | None:
    """Read a single passage by its chunk_id, e.g. to double-check a citation before answering."""
    return await retriever.read_chunk(ctx.deps.supabase_client, chunk_id)


@agent.tool
async def read_surrounding_chunks(
    ctx: RunContext[DocumentAgentDeps], chunk_id: str, before: int = 1, after: int = 1
) -> list[SourcePassage]:
    """Read the passages immediately before/after a given chunk, for more surrounding context."""
    return await retriever.read_surrounding_chunks(ctx.deps.supabase_client, chunk_id, before, after)
