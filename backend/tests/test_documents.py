"""
Document API tests.

Tests document listing, retrieval, deletion, and text processing endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, FileType, ProcessingStatus
from app.models.user import User


# ---------------------------------------------------------------------------
# Helper to create a test document in the database
# ---------------------------------------------------------------------------

async def create_test_document(
    db_session: AsyncSession,
    user: User,
    filename: str = "test.pdf",
    file_type: FileType = FileType.PDF,
    extracted_text: str = "Sample extracted text content.",
    status: ProcessingStatus = ProcessingStatus.COMPLETED,
) -> Document:
    """Create a test document record."""
    doc = Document(
        user_id=user.id,
        filename=filename,
        file_type=file_type,
        extracted_text=extracted_text,
        status=status,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Listing tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient, auth_headers: dict):
    """Test listing documents when user has none."""
    response = await client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["documents"] == []


@pytest.mark.asyncio
async def test_list_documents_with_data(
    client: AsyncClient, auth_headers: dict,
    db_session: AsyncSession, test_user: User,
):
    """Test listing documents when user has documents."""
    await create_test_document(db_session, test_user, "notes1.pdf")
    await create_test_document(db_session, test_user, "notes2.pdf")

    response = await client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["documents"]) == 2


@pytest.mark.asyncio
async def test_list_documents_unauthenticated(client: AsyncClient):
    """Test listing documents without auth returns 401."""
    response = await client.get("/api/v1/documents")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Retrieval tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_document_success(
    client: AsyncClient, auth_headers: dict,
    db_session: AsyncSession, test_user: User,
):
    """Test retrieving a specific document."""
    doc = await create_test_document(db_session, test_user)

    response = await client.get(f"/api/v1/documents/{doc.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert data["filename"] == "test.pdf"
    assert data["extracted_text"] == "Sample extracted text content."


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, auth_headers: dict):
    """Test retrieving a non-existent document returns 404."""
    response = await client.get(
        "/api/v1/documents/nonexistent-id", headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_document_other_user(
    client: AsyncClient, auth_headers: dict,
    db_session: AsyncSession, test_educator: User,
):
    """Test that a user cannot access another user's document."""
    # Create document owned by educator
    doc = await create_test_document(db_session, test_educator)

    # Try to access with student's token
    response = await client.get(f"/api/v1/documents/{doc.id}", headers=auth_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Deletion tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_document_success(
    client: AsyncClient, auth_headers: dict,
    db_session: AsyncSession, test_user: User,
):
    """Test deleting a document."""
    doc = await create_test_document(db_session, test_user)

    response = await client.delete(f"/api/v1/documents/{doc.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify it's gone
    response = await client.get(f"/api/v1/documents/{doc.id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(client: AsyncClient, auth_headers: dict):
    """Test deleting a non-existent document returns 404."""
    response = await client.delete(
        "/api/v1/documents/nonexistent-id", headers=auth_headers
    )
    assert response.status_code == 404
