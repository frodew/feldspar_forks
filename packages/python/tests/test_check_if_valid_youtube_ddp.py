"""Tests for check_if_valid_youtube_ddp's "My Activity" export detection."""

import io
import json
import sys
import zipfile
from pathlib import Path

# Add packages/python to sys.path so the `port` package resolves.
sys.path.insert(0, str(Path(__file__).parent.parent))

from port.script import check_if_valid_youtube_ddp


def _zip_of(files: dict[str, bytes]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf


def _my_activity_json_entry(product="YouTube"):
    return {"time": "2026-01-01T00:00:00Z", "products": [product]}


def test_my_activity_json_single_folder_is_valid():
    entries = [_my_activity_json_entry() for _ in range(5)]
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(entries),
        }
    )
    assert check_if_valid_youtube_ddp(zf) == "valid_my_activity"


def test_my_activity_html_single_folder_is_invalid_no_json():
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.html": "<html></html>",
        }
    )
    assert check_if_valid_youtube_ddp(zf) == "invalid_no_json"


def test_my_activity_html_with_sibling_product_folders_still_detected():
    zf = _zip_of(
        {
            "Meine Aktivitäten/Anfrage zur Datenfreigabe/MeineAktivitäten.html": "<html></html>",
            "Meine Aktivitäten/Datenexport/MeineAktivitäten.html": "<html></html>",
            "Meine Aktivitäten/Gemini-Apps/MeineAktivitäten.html": "<html></html>",
            "Meine Aktivitäten/Gemini-Apps/image-1.png": b"\x89PNG",
            "Meine Aktivitäten/YouTube/MeineAktivitäten.html": "<html></html>",
        }
    )
    assert check_if_valid_youtube_ddp(zf) == "invalid_no_json"


def test_unrelated_zip_is_invalid_no_ddp():
    zf = _zip_of({"some_other_export/readme.txt": "hello"})
    assert check_if_valid_youtube_ddp(zf) == "invalid_no_ddp"
