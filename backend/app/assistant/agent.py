from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.settings import ModelSettings

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

agent = Agent(
    _model,
    deps_type=DocumentAgentDeps,
    output_type=GroundedAnswer,
    instructions=_INSTRUCTIONS,
    # Lower than the provider default (1.0) — this agent answers from cited source text, not
    # creative generation, so less sampling variance means steadier grounding/citation formatting.
    model_settings=ModelSettings(temperature=0.4),
)

_title_agent = Agent(
    _model,
    output_type=str,
    instructions=(
        "Summarize the user's message as a short chat title: 3-6 words, plain text, no "
        "surrounding quotes, no trailing punctuation, same language as the message."
    ),
)


async def generate_title(text: str) -> str:
    result = await _title_agent.run(text)
    return result.output.strip()


@agent.tool
async def search_documents(
    ctx: RunContext[DocumentAgentDeps], query: str, group_code: str | None = None
) -> list[SourcePassage]:
    """Search the internal document corpus for passages relevant to the query. If the user
    names a specific document set (e.g. a contract number), pass its code as group_code to
    scope the search to just that contract and its appendices instead of the whole corpus."""
    return await retriever.search_documents(ctx.deps.supabase_client, query, group_code=group_code)


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
