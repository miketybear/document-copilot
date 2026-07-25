from openai import AzureOpenAI

from app.config import settings

_BATCH_SIZE = 100

_client: AzureOpenAI | None = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = _get_client().embeddings.create(
            input=batch,
            model=settings.azure_openai_embedding_deployment,
            dimensions=settings.azure_openai_embedding_dimensions,
        )
        embeddings.extend(item.embedding for item in response.data)
    return embeddings


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
