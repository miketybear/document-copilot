import uuid
from datetime import date, datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CitationKind(StrEnum):
    document = "document"  # a document_chunks passage, subject to grounding validation
    tool_source = "tool_source"  # an MCP tool call — provenance only, not grounding-checked


class MessageCitation(Base):
    __tablename__ = "message_citations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    citation_kind: Mapped[CitationKind] = mapped_column(
        Enum(CitationKind, name="citation_kind"), nullable=False, server_default=CitationKind.document.value
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id"), nullable=True, index=True
    )
    # Populated when citation_kind == tool_source: {"system": ..., "record_type": ..., "tool_name": ...}
    tool_source: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MCPAuthType(StrEnum):
    api_token = "api_token"
    oauth2 = "oauth2"


class MCPConnectionStatus(StrEnum):
    pending = "pending"  # oauth2 only: created, waiting on the user to complete the authorize redirect
    connected = "connected"
    token_expired = "token_expired"
    error = "error"


class MCPConnection(Base):
    """A shared, admin-managed connection to an external MCP server. Not per-user: internal
    systems like Maximo/BPM are typically integrated via one service credential rather than
    per-employee OAuth, and that keeps end-user setup to zero."""

    __tablename__ = "mcp_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    server_url: Mapped[str] = mapped_column(String, nullable=False)
    auth_type: Mapped[MCPAuthType] = mapped_column(Enum(MCPAuthType, name="mcp_auth_type"), nullable=False)
    status: Mapped[MCPConnectionStatus] = mapped_column(
        Enum(MCPConnectionStatus, name="mcp_connection_status"),
        nullable=False,
        server_default=MCPConnectionStatus.pending.value,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # api_token auth
    encrypted_api_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # oauth2 auth — tokens plus enough of the client registration to refresh later without
    # re-running discovery/dynamic client registration.
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    oauth_client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    encrypted_oauth_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_token_endpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    # Transient PKCE state for the in-flight authorize round trip; cleared once the callback
    # exchanges the code for tokens.
    oauth_state: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    oauth_pkce_verifier: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DocumentType(StrEnum):
    policy = "policy"
    guideline = "guideline"
    work_instruction = "work_instruction"
    contract = "contract"


class DocumentStatus(StrEnum):
    current = "current"
    superseded = "superseded"


class DocumentGroup(Base):
    """Groups related source documents (e.g. a contract and its appendices) so they can be
    filtered/expanded together at retrieval time, independent of each member's own supersede
    lifecycle."""

    __tablename__ = "document_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    group_code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, name="document_type"), nullable=False)
    department: Mapped[str | None] = mapped_column(String, nullable=True)
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), nullable=False, server_default=DocumentStatus.current.value
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id"), nullable=True
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_groups.id"), nullable=True, index=True
    )
    doc_role: Mapped[str | None] = mapped_column(String, nullable=True)
    source_location: Mapped[str | None] = mapped_column(String, nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Dimension is tied to the configured embedding deployment; changing deployments requires a new migration.
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.azure_openai_embedding_dimensions), nullable=False)
    # Populated by a generated column (see migration) — not written to directly.
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
