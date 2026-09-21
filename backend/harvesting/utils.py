"""
Harvesting utilities.

- IST-aware date handling
- SHA-256 calculation
- Storage path generation
- Filename sanitisation
"""

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pytz


IST = pytz.timezone("Asia/Kolkata")


def get_ist_date(offset_days: int = 0) -> date:
    """Return today's date in IST (Asia/Kolkata), with optional day offset."""
    now = datetime.now(IST)
    from datetime import timedelta
    return (now + timedelta(days=offset_days)).date()


def get_ist_now() -> datetime:
    """Return current datetime in IST."""
    return datetime.now(IST)


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file (streaming, 64 KB chunks)."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_newspaper_storage_path(
    storage_root: Path,
    source_id: str,
    target_date: date,
    edition_name: str,
) -> Path:
    """
    Build a structured storage path for a downloaded newspaper PDF.

    Layout:
        storage/newspapers/{source_id}/{yyyy}/{mm}/{dd}/{edition}.pdf
    """
    safe_edition = sanitise_filename(edition_name) or "default"
    return (
        storage_root
        / "newspapers"
        / source_id
        / str(target_date.year)
        / f"{target_date.month:02d}"
        / f"{target_date.day:02d}"
        / f"{safe_edition}.pdf"
    )


def sanitise_filename(name: str) -> str:
    """Remove characters that are unsafe in filenames."""
    return re.sub(r"[^\w\-]", "_", name.strip().lower())


def substitute_date_in_url(url_template: str, target_date: date) -> str:
    """
    Replace date placeholders in a URL template.

    Supported tokens:
        {yyyy}  — four-digit year
        {mm}    — two-digit month
        {dd}    — two-digit day
        {yy}    — two-digit year
        {m}     — month without leading zero
        {d}     — day without leading zero
    """
    return (
        url_template
        .replace("{yyyy}", str(target_date.year))
        .replace("{yy}", str(target_date.year)[-2:])
        .replace("{mm}", f"{target_date.month:02d}")
        .replace("{m}", str(target_date.month))
        .replace("{dd}", f"{target_date.day:02d}")
        .replace("{d}", str(target_date.day))
    )
