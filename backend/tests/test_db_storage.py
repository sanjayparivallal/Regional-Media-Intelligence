"""
Tests for DBStorageService (PostgreSQL-backed storage).
"""

import os
import uuid
import pytest
from storage.db_storage_service import DBStorageService


@pytest.fixture
def storage():
    return DBStorageService()


def test_db_storage_crud(storage):
    test_id = f"test-brand-{uuid.uuid4().hex[:8]}"

    # 1. Append row
    storage.append_row("MonitoredBrands", {
        "brand_id": test_id,
        "brand_name": "Test Brand Pytest",
        "aliases": "TBP,TestBP",
        "industry": "Fintech",
        "enabled": True,
        "dynamic_pytest_field": "Extra Value 123",
    })

    # 2. Find row
    brand = storage.find_row("MonitoredBrands", {"brand_id": test_id})
    assert brand is not None
    assert brand["brand_name"] == "Test Brand Pytest"
    assert brand["dynamic_pytest_field"] == "Extra Value 123"

    # 3. Update row
    updated = storage.update_row(
        "MonitoredBrands",
        {"brand_id": test_id},
        {"brand_name": "Updated Brand Pytest", "another_col": "456"}
    )
    assert updated is True

    brand_upd = storage.find_row("MonitoredBrands", {"brand_id": test_id})
    assert brand_upd is not None
    assert brand_upd["brand_name"] == "Updated Brand Pytest"
    assert brand_upd["another_col"] == "456"

    # 4. Delete row
    deleted = storage.delete_row("MonitoredBrands", {"brand_id": test_id})
    assert deleted is True

    brand_none = storage.find_row("MonitoredBrands", {"brand_id": test_id})
    assert brand_none is None


def test_missing_column_query_resilience(storage):
    """Querying a non-existent column must never raise an UndefinedColumn error."""
    # Non-existent column with non-empty value -> matches 0 rows, no error
    rows = storage.find_rows("Translations", {"this_column_does_not_exist_at_all": "some_uuid"})
    assert rows == []

    # Non-existent column delete_rows -> deletes 0 rows, no error
    deleted = storage.delete_rows("Translations", {"this_column_does_not_exist_at_all": "some_uuid"})
    assert deleted == 0


def test_translations_document_id(storage):
    """Translations table must have document_id and support delete_rows/find_rows."""
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    t_id = f"trans-{uuid.uuid4().hex[:8]}"

    storage.append_row("Translations", {
        "translation_id": t_id,
        "article_id": "art-99",
        "document_id": doc_id,
        "source_language": "ta",
        "target_language": "en",
        "original_text": "வணக்கம்",
        "translated_text": "Hello",
    })

    # Verify document_id querying works
    rows = storage.find_rows("Translations", {"document_id": doc_id})
    assert len(rows) == 1
    assert rows[0]["document_id"] == doc_id
    assert rows[0]["translated_text"] == "Hello"

    # Verify delete_rows by document_id works (used by processor.py to clear previous run)
    del_count = storage.delete_rows("Translations", {"document_id": doc_id})
    assert del_count == 1

    # Verify deleted
    rows_after = storage.find_rows("Translations", {"document_id": doc_id})
    assert len(rows_after) == 0
