import uuid

import pytest

from app.database.supabase import get_service_role_client
from ingest.load import upsert_document

pytestmark = pytest.mark.integration


def _doc_kwargs(**overrides):
    kwargs = dict(
        title="Test Document",
        document_type="policy",
        department=None,
        owner=None,
        version=None,
        effective_date=None,
        source_location="test.pdf",
        content_markdown="# Test\ncontent",
    )
    kwargs.update(overrides)
    return kwargs


async def test_reingesting_same_title_and_group_supersedes_previous_version(cleanup_rows):
    group_code = f"group-{uuid.uuid4()}"
    title = f"Contract {uuid.uuid4()}"

    first_id = await upsert_document(**_doc_kwargs(title=title, group_code=group_code, doc_role="main"))
    second_id = await upsert_document(**_doc_kwargs(title=title, group_code=group_code, doc_role="main"))
    cleanup_rows["source_documents"] += [first_id, second_id]

    client = await get_service_role_client()
    first = await client.table("source_documents").select("status,superseded_by,group_id").eq("id", first_id).single().execute()
    second = await client.table("source_documents").select("status,group_id").eq("id", second_id).single().execute()
    cleanup_rows["document_groups"].append(second.data["group_id"])

    assert first.data["status"] == "superseded"
    assert first.data["superseded_by"] == second_id
    assert second.data["status"] == "current"
    assert first.data["group_id"] == second.data["group_id"]


async def test_same_title_in_different_groups_does_not_supersede(cleanup_rows):
    title = f"Appendix {uuid.uuid4()}"
    group_a = f"group-{uuid.uuid4()}"
    group_b = f"group-{uuid.uuid4()}"

    doc_a = await upsert_document(**_doc_kwargs(title=title, group_code=group_a))
    doc_b = await upsert_document(**_doc_kwargs(title=title, group_code=group_b))
    cleanup_rows["source_documents"] += [doc_a, doc_b]

    client = await get_service_role_client()
    a = await client.table("source_documents").select("status,group_id").eq("id", doc_a).single().execute()
    b = await client.table("source_documents").select("status,group_id").eq("id", doc_b).single().execute()
    cleanup_rows["document_groups"] += [a.data["group_id"], b.data["group_id"]]

    assert a.data["status"] == "current"
    assert b.data["status"] == "current"
    assert a.data["group_id"] != b.data["group_id"]


async def test_ungrouped_document_with_same_title_as_grouped_one_does_not_supersede(cleanup_rows):
    title = f"Shared Title {uuid.uuid4()}"
    group_code = f"group-{uuid.uuid4()}"

    grouped_id = await upsert_document(**_doc_kwargs(title=title, group_code=group_code))
    ungrouped_id = await upsert_document(**_doc_kwargs(title=title))
    cleanup_rows["source_documents"] += [grouped_id, ungrouped_id]

    client = await get_service_role_client()
    grouped = await client.table("source_documents").select("status,group_id").eq("id", grouped_id).single().execute()
    ungrouped = await client.table("source_documents").select("status,group_id").eq("id", ungrouped_id).single().execute()
    cleanup_rows["document_groups"].append(grouped.data["group_id"])

    assert grouped.data["status"] == "current"
    assert ungrouped.data["status"] == "current"
    assert ungrouped.data["group_id"] is None


async def test_reingesting_same_title_without_group_still_supersedes(cleanup_rows):
    title = f"Standalone Doc {uuid.uuid4()}"

    first_id = await upsert_document(**_doc_kwargs(title=title))
    second_id = await upsert_document(**_doc_kwargs(title=title))
    cleanup_rows["source_documents"] += [first_id, second_id]

    client = await get_service_role_client()
    first = await client.table("source_documents").select("status,superseded_by").eq("id", first_id).single().execute()

    assert first.data["status"] == "superseded"
    assert first.data["superseded_by"] == second_id


async def test_group_is_created_once_and_reused_across_member_documents(cleanup_rows):
    group_code = f"group-{uuid.uuid4()}"

    main_id = await upsert_document(
        **_doc_kwargs(title=f"Main {uuid.uuid4()}", group_code=group_code, group_title="My Contract", doc_role="main")
    )
    appendix_id = await upsert_document(
        **_doc_kwargs(title=f"Appendix {uuid.uuid4()}", group_code=group_code, doc_role="appendix")
    )
    cleanup_rows["source_documents"] += [main_id, appendix_id]

    client = await get_service_role_client()
    main = await client.table("source_documents").select("group_id").eq("id", main_id).single().execute()
    appendix = await client.table("source_documents").select("group_id").eq("id", appendix_id).single().execute()
    group = await client.table("document_groups").select("title").eq("id", main.data["group_id"]).single().execute()
    cleanup_rows["document_groups"].append(main.data["group_id"])

    assert main.data["group_id"] == appendix.data["group_id"]
    assert group.data["title"] == "My Contract"
