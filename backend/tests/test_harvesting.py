"""
Unit and integration tests for RMIA ePaper harvesting system.
"""

import asyncio
import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from harvesting.core.downloader import PDFDownloader
from harvesting.core.models import (
    AttemptStatus,
    EditionConfig,
    HarvestAttempt,
    HarvestJob,
    HarvestResult,
    HarvestStatus,
    NewspaperSource,
    SourceType,
)
from harvesting.core.registry import HarvesterRegistry
from harvesting.core.storage import HarvestStorage
from harvesting.core.validator import PDFValidator, ValidationStatus
from harvesting.exceptions import (
    AuthRequired,
    CaptchaRequired,
    DownloadFailed,
    Duplicate,
    EmptyFile,
    HarvestError,
    InvalidPDF,
)
from harvesting.harvesters.direct_pdf import DirectPDFHarvester
from harvesting.service import HarvestingService
from harvesting.utils import (
    calculate_sha256,
    get_ist_date,
    get_ist_now,
    make_newspaper_storage_path,
    sanitise_filename,
    substitute_date_in_url,
)


# ---------------------------------------------------------------------------
# 1. Config & Models
# ---------------------------------------------------------------------------

def test_source_model_valid():
    source = NewspaperSource(
        id="test_epaper",
        name="Test ePaper",
        publisher="Test Media",
        language="Hindi",
        language_code="hi",
        region="Delhi",
        source_type=SourceType.DIRECT_PDF,
        url_template="https://example.com/{yyyy}/{mm}/{dd}.pdf",
    )
    assert source.id == "test_epaper"
    assert source.source_type == SourceType.DIRECT_PDF
    assert source.enabled is True
    assert source.requires_login is False


def test_load_sources_from_json():
    service = HarvestingService()
    service.load_sources()
    sources = service.get_sources()
    assert len(sources) >= 3
    
    # Check that seed sources exist
    ids = {s.id for s in sources}
    assert "daily_thanthi" in ids
    assert "eenadu_telugu" in ids
    assert "dainik_jagran" in ids


# ---------------------------------------------------------------------------
# 2. Date Utilities & URL Template Substitution
# ---------------------------------------------------------------------------

def test_ist_date_utilities():
    today_ist = get_ist_date()
    assert isinstance(today_ist, date)
    
    yesterday_ist = get_ist_date(-1)
    assert (today_ist - yesterday_ist).days == 1
    
    now_ist = get_ist_now()
    assert isinstance(now_ist, datetime)
    assert now_ist.tzinfo is not None


def test_substitute_date_in_url():
    template = "https://example.com/epaper/{yyyy}/{mm}/{dd}/page_{yy}{m}{d}.pdf"
    target = date(2026, 9, 5)
    resolved = substitute_date_in_url(template, target)
    assert resolved == "https://example.com/epaper/2026/09/05/page_2695.pdf"


# ---------------------------------------------------------------------------
# 3. Path & Filename Sanitisation & SHA-256
# ---------------------------------------------------------------------------

def test_sanitise_filename():
    assert sanitise_filename("Hyderabad Main (City)") == "hyderabad_main__city_"
    assert sanitise_filename("edition-1_new") == "edition-1_new"


def test_make_newspaper_storage_path(tmp_path):
    p = make_newspaper_storage_path(tmp_path, "eenadu", date(2026, 9, 20), "hyderabad")
    assert p == tmp_path / "newspapers" / "eenadu" / "2026" / "09" / "20" / "hyderabad.pdf"


def test_calculate_sha256(tmp_path):
    test_file = tmp_path / "test.bin"
    test_file.write_bytes(b"hello media intelligence")
    import hashlib
    expected = hashlib.sha256(b"hello media intelligence").hexdigest()
    assert calculate_sha256(test_file) == expected


# ---------------------------------------------------------------------------
# 4. PDF Validator
# ---------------------------------------------------------------------------

def test_pdf_validator_not_found(tmp_path):
    validator = PDFValidator()
    assert validator.validate(tmp_path / "nonexistent.pdf") == ValidationStatus.NOT_FOUND


def test_pdf_validator_empty_or_small(tmp_path):
    validator = PDFValidator()
    small_file = tmp_path / "small.pdf"
    small_file.write_bytes(b"%PDF-1.4 but too short")
    assert validator.validate(small_file) == ValidationStatus.EMPTY_FILE


def test_pdf_validator_invalid_magic_bytes(tmp_path):
    validator = PDFValidator()
    garbage_file = tmp_path / "garbage.pdf"
    garbage_file.write_bytes(b"NOT_A_PDF" + b"A" * 2000)
    assert validator.validate(garbage_file) == ValidationStatus.INVALID_PDF


def test_pdf_validator_valid_pdf(tmp_path):
    import fitz
    pdf_path = tmp_path / "valid.pdf"
    doc = fitz.open()
    for _ in range(5):
        page = doc.new_page()
        page.insert_text((50, 72), "RMIA Automated Harvesting Test Page " * 50)
    doc.save(str(pdf_path))
    doc.close()

    # Ensure size > 1024
    assert pdf_path.stat().st_size >= 1024

    validator = PDFValidator()
    assert validator.validate(pdf_path) == ValidationStatus.VALID


# ---------------------------------------------------------------------------
# 5. Harvester Registry
# ---------------------------------------------------------------------------

def test_harvester_registry():
    src_direct = NewspaperSource(
        id="s1", name="S1", publisher="P", language="en", language_code="en",
        region="R", source_type=SourceType.DIRECT_PDF, url_template="http://example.com/test.pdf"
    )
    harvester = HarvesterRegistry.get(src_direct)
    assert isinstance(harvester, DirectPDFHarvester)


# ---------------------------------------------------------------------------
# 6. PDF Downloader (Mocked HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pdf_downloader_success(tmp_path):
    dest = tmp_path / "downloaded.pdf"
    downloader = PDFDownloader(max_retries=1)

    # Generate dummy bytes > 1024
    content = b"%PDF-1.5\n" + (b"0123456789abcdef" * 100)

    class MockStreamContext:
        def __init__(self, *args, **kwargs):
            self.status_code = 200
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def aiter_bytes(self, chunk_size):
            yield content

    class MockClientContext:
        async def __aenter__(self):
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=MockStreamContext())
            return mock_client
        async def __aexit__(self, *args):
            pass

    with patch("httpx.AsyncClient", return_value=MockClientContext()):
        size = await downloader.download("http://mock.test/paper.pdf", dest)
        assert size == len(content)
        assert dest.exists()
        assert dest.read_bytes() == content


@pytest.mark.asyncio
async def test_pdf_downloader_http_error(tmp_path):
    dest = tmp_path / "failed.pdf"
    downloader = PDFDownloader(max_retries=1)

    class MockStreamContext:
        def __init__(self, *args, **kwargs):
            self.status_code = 404
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def aiter_bytes(self, chunk_size):
            yield b""

    class MockClientContext:
        async def __aenter__(self):
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=MockStreamContext())
            return mock_client
        async def __aexit__(self, *args):
            pass

    with patch("httpx.AsyncClient", return_value=MockClientContext()):
        with pytest.raises(DownloadFailed):
            await downloader.download("http://mock.test/404.pdf", dest)


# ---------------------------------------------------------------------------
# 7. Harvesting Service & Error Isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_harvest_service_error_isolation(tmp_path):
    """
    Verify that when one source fails or requires auth, other sources
    still run and complete successfully (error isolation).
    """
    service = HarvestingService()
    service._storage = MagicMock()
    service._storage.sha256_exists.return_value = False
    service._submit_to_pipeline = AsyncMock(return_value="doc-12345")

    # Source 1: Succeeds
    s1 = NewspaperSource(
        id="source_ok", name="Good News", publisher="Pub1", language="en", language_code="en",
        region="R1", source_type=SourceType.DIRECT_PDF, url_template="http://good.com/pdf",
        enabled=True
    )
    # Source 2: Fails with AuthRequired
    s2 = NewspaperSource(
        id="source_auth", name="Protected News", publisher="Pub2", language="en", language_code="en",
        region="R2", source_type=SourceType.DIRECT_PDF, url_template="http://auth.com/pdf",
        requires_login=True, enabled=True
    )
    # Source 3: Fails with download error
    s3 = NewspaperSource(
        id="source_fail", name="Broken News", publisher="Pub3", language="en", language_code="en",
        region="R3", source_type=SourceType.DIRECT_PDF, url_template="http://broken.com/pdf",
        enabled=True
    )

    service._sources = [s1, s2, s3]
    service._loaded = True

    # Mock _harvest_source per source
    async def mock_harvest_source(source, target_date, job_id, semaphore):
        if source.id == "source_ok":
            return HarvestAttempt(
                job_id=job_id,
                source_id=source.id,
                source_name=source.name,
                language=source.language,
                language_code=source.language_code,
                target_date=target_date.isoformat(),
                status=AttemptStatus.PIPELINE_SUBMITTED,
                edition_name="main",
                file_path="/tmp/good.pdf",
                document_id="doc-good-1",
            )
        elif source.id == "source_auth":
            return HarvestAttempt(
                job_id=job_id,
                source_id=source.id,
                source_name=source.name,
                edition_name="main",
                language=source.language,
                language_code=source.language_code,
                target_date=target_date.isoformat(),
                status=AttemptStatus.AUTH_REQUIRED,
                error_type="AuthRequired",
                error_message="Login session expired",
            )
        else:
            return HarvestAttempt(
                job_id=job_id,
                source_id=source.id,
                source_name=source.name,
                edition_name="main",
                language=source.language,
                language_code=source.language_code,
                target_date=target_date.isoformat(),
                status=AttemptStatus.FAILED,
                error_type="DownloadFailed",
                error_message="HTTP 500 server error",
            )

    service._harvest_source = mock_harvest_source

    result = await service.run_harvest(target_date=date(2026, 9, 20), source_ids=["source_ok", "source_auth", "source_fail"])

    # Verify overall result
    assert result.total_sources == 3
    assert result.successful == 1
    assert result.failed == 1
    assert result.auth_required == 1
    assert len(result.attempts) == 3
