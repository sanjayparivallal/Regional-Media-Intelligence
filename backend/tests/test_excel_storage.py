"""
Unit tests for ExcelStorageService.
"""

import tempfile
from pathlib import Path
from storage.excel_storage_service import ExcelStorageService


def test_excel_storage_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_rmi_db.xlsx"
        storage = ExcelStorageService(excel_path=str(test_file))

        # 1. Check file created
        assert test_file.exists()

        # 2. Append row
        storage.append_row("MonitoredBrands", {
            "brand_id": "b-101",
            "brand_name": "Test Brand",
            "aliases": "TB,TestB",
            "industry": "Fintech",
            "enabled": True,
            "custom_field": "Extra Value",  # Dynamic column
        })

        # 3. Find rows
        brands = storage.find_rows("MonitoredBrands", {"enabled": True})
        assert len(brands) == 1
        assert brands[0]["brand_name"] == "Test Brand"
        assert brands[0]["custom_field"] == "Extra Value"

        # 4. Find row
        b = storage.find_row("MonitoredBrands", {"brand_id": "b-101"})
        assert b is not None
        assert b["brand_id"] == "b-101"

        # 5. Update row
        updated = storage.update_row("MonitoredBrands", {"brand_id": "b-101"}, {
            "brand_name": "Updated Brand",
            "new_attr": 42,
        })
        assert updated is True

        b_updated = storage.find_row("MonitoredBrands", {"brand_id": "b-101"})
        assert b_updated is not None
        assert b_updated["brand_name"] == "Updated Brand"
        assert b_updated["new_attr"] == 42

        # 6. Delete row
        deleted = storage.delete_row("MonitoredBrands", {"brand_id": "b-101"})
        assert deleted is True

        b_none = storage.find_row("MonitoredBrands", {"brand_id": "b-101"})
        assert b_none is None


def test_seed_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_seed.xlsx"
        storage = ExcelStorageService(excel_path=str(test_file))

        # Initially empty
        assert len(storage.find_rows("MonitoredBrands")) == 0

        # Seed defaults
        storage.seed_defaults_if_empty()
        brands = storage.find_rows("MonitoredBrands")
        assert len(brands) > 0
