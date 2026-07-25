from app.retrieval import retriever

DOC_META = {
    "title": "Doc One",
    "document_type": "policy",
    "department": "HR",
    "version": "1.0",
    "effective_date": "2024-01-01",
}
ROW_A = {
    "id": "chunk-a",
    "document_id": "doc-1",
    "chunk_index": 0,
    "heading_path": ["Intro"],
    "chunk_text": "text a",
    "source_documents": DOC_META,
}
ROW_B = {
    "id": "chunk-b",
    "document_id": "doc-1",
    "chunk_index": 1,
    "heading_path": ["Intro"],
    "chunk_text": "text b",
    "source_documents": DOC_META,
}


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTableQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    async def execute(self):
        return FakeResponse(self._data)


class FakeRpcQuery:
    def __init__(self, data):
        self._data = data

    async def execute(self):
        return FakeResponse(self._data)


class FakeClient:
    def __init__(self, table_rows, rpc_rows):
        self.table_rows = table_rows
        self.rpc_rows = rpc_rows

    def table(self, _name):
        return FakeTableQuery(self.table_rows)

    def rpc(self, name, _params):
        return FakeRpcQuery(self.rpc_rows[name])


async def test_search_documents_fuses_rankings_and_returns_passages(monkeypatch):
    monkeypatch.setattr(retriever, "embed_query", lambda _text: [0.0, 0.0, 0.0])

    client = FakeClient(
        table_rows=[ROW_A, ROW_B],
        rpc_rows={
            "search_chunks_semantic": [{"id": "chunk-a"}, {"id": "chunk-b"}],
            "search_chunks_fulltext": [{"id": "chunk-a"}, {"id": "chunk-b"}],
        },
    )

    results = await retriever.search_documents(client, "some query", k=2)

    assert [p.chunk_id for p in results] == ["chunk-a", "chunk-b"]
    assert results[0].document_title == "Doc One"
    assert results[0].heading_path == ["Intro"]


async def test_search_documents_with_no_matches_returns_empty(monkeypatch):
    monkeypatch.setattr(retriever, "embed_query", lambda _text: [0.0, 0.0, 0.0])

    client = FakeClient(table_rows=[], rpc_rows={"search_chunks_semantic": [], "search_chunks_fulltext": []})

    results = await retriever.search_documents(client, "no matches", k=2)

    assert results == []


async def test_read_chunk_returns_matching_passage():
    client = FakeClient(table_rows=[ROW_A], rpc_rows={})

    passage = await retriever.read_chunk(client, "chunk-a")

    assert passage is not None
    assert passage.chunk_id == "chunk-a"
    assert passage.chunk_text == "text a"


async def test_read_chunk_returns_none_when_missing():
    client = FakeClient(table_rows=[], rpc_rows={})

    assert await retriever.read_chunk(client, "missing") is None


async def test_read_surrounding_chunks_returns_neighbors():
    client = FakeClient(table_rows=[ROW_A, ROW_B], rpc_rows={})

    passages = await retriever.read_surrounding_chunks(client, "chunk-a", before=1, after=1)

    assert [p.chunk_id for p in passages] == ["chunk-a", "chunk-b"]
