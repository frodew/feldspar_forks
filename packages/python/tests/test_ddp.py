"""Tests for reading a Takeout ZIP: what counts as a valid DDP, and what gets pooled."""

import io
import json
import sys
import zipfile
from pathlib import Path

# Add packages/python to sys.path so the `port` package resolves.
sys.path.insert(0, str(Path(__file__).parent.parent))

from port.behaviors.subscriptions import extract_subscriptions
from port.behaviors.watch_history import extract_watch_history
from port.ddp import YoutubeDdp
from tests.html_fixtures import activity_html, searched_cell, watched_cell

SUBS_CSV = (
    "Kanal-ID,Kanal-URL,Kanaltitel\n"
    "UCcsv,http://www.youtube.com/channel/UCcsv,Aus CSV\n"
)
COMMENTS_CSV = (
    "Kommentar-ID,Kanal-ID,Erstellungszeitstempel,Preis,Video-ID,Kommentartext\n"
    'Ugxabc,UCabc,2026-01-01T00:00:00Z,,vid1,"{""text"": ""hallo""}"\n'
)


def _zip_of(files: dict[str, bytes]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf


def _watch(video_id, product="YouTube"):
    return {
        "header": "YouTube",
        "title": f"Video {video_id} angesehen",
        "titleUrl": f"https://www.youtube.com/watch?v={video_id}",
        "time": "2026-01-01T00:00:00Z",
        "products": [product],
        "activityControls": ["YouTube-Wiedergabeverlauf"],
    }


def _homepage_ad(time="2026-01-01T00:00:00Z"):
    """An ad impression on the YouTube homepage: no titleUrl at all."""
    return {
        "header": "YouTube",
        "title": "Hat Anzeigen auf der YouTube-Startseite angesehen",
        "time": time,
        "products": ["YouTube"],
        "details": [{"name": "Von Google Anzeigen"}],
        "activityControls": ["Web- & App-Aktivitäten"],
    }


def test_my_activity_ddp_json_is_valid():
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch("vid1")]
            )
        }
    )
    assert YoutubeDdp(zf).verdict == "valid"


def test_my_activity_ddp_html_is_valid():
    """An HTML DDP is donatable, not a dead end."""
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.html": activity_html(
                watched_cell("vid1")
            )
        }
    )
    ddp = YoutubeDdp(zf)
    assert ddp.verdict == "valid"
    assert len(ddp.entries) == 1


def test_youtube_ddp_html_history_is_valid():
    zf = _zip_of(
        {
            "Takeout/YouTube und YouTube Music/Verlauf/Wiedergabeverlauf.html": activity_html(
                watched_cell("vid1")
            ),
            "Takeout/YouTube und YouTube Music/Verlauf/Suchverlauf.html": activity_html(
                searched_cell("katzen")
            ),
        }
    )
    assert YoutubeDdp(zf).verdict == "valid"
    assert len(extract_watch_history(zf)) == 1


def test_youtube_ddp_without_history_is_valid_on_its_csvs_alone():
    zf = _zip_of({"Takeout/YouTube und YouTube Music/Abos/Abos.csv": SUBS_CSV})
    ddp = YoutubeDdp(zf)
    assert ddp.verdict == "valid"
    assert ddp.entries == []
    assert ddp.subscriptions_csv is not None


def test_my_activity_ddp_without_youtube_is_not_a_ddp():
    """Another product's activity file is not YouTube data."""
    zf = _zip_of(
        {
            "Meine Aktivitäten/Gmail/MeineAktivitäten.json": json.dumps(
                [_watch("m1", product="Gmail")]
            ),
            "Meine Aktivitäten/Flüge/MeineAktivitäten.json": json.dumps(
                [_watch("f1", product="Flüge")]
            ),
        }
    )
    assert YoutubeDdp(zf).verdict == "invalid_no_ddp"


def test_html_without_activity_cells_is_not_a_ddp():
    zf = _zip_of({"Meine Aktivitäten/YouTube/MeineAktivitäten.html": "<html></html>"})
    assert YoutubeDdp(zf).verdict == "invalid_no_ddp"


def test_unrelated_zip_is_not_a_ddp():
    assert YoutubeDdp(_zip_of({"some_other_export/readme.txt": "hello"})).verdict == (
        "invalid_no_ddp"
    )


def test_unrelated_html_outside_youtube_folders_is_ignored():
    """Chrome bookmarks are HTML even in a JSON Takeout - not our concern."""
    zf = _zip_of(
        {
            "Takeout/Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch("vid1")]
            ),
            "Takeout/Chrome/Lesezeichen.html": "<html></html>",
        }
    )
    ddp = YoutubeDdp(zf)
    assert ddp.verdict == "valid"
    assert len(ddp.entries) == 1


def test_a_file_that_is_not_a_zip_is_reported_as_such():
    assert YoutubeDdp(io.BytesIO(b"not a zip at all")).verdict == "invalid_file_zip"


def test_json_wins_over_html_so_no_row_is_counted_twice():
    """A participant could export both formats; the rows are the same rows."""
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch("vid1")]
            ),
            "Meine Aktivitäten/YouTube/MeineAktivitäten.html": activity_html(
                watched_cell("vid1")
            ),
        }
    )
    ddp = YoutubeDdp(zf)
    assert len(ddp.entries) == 1
    assert ddp.sources.endswith(".json")


def test_pooled_entries_keep_the_member_they_came_from():
    zf = _zip_of(
        {
            "Takeout/YouTube und YouTube Music/Verlauf/Wiedergabeverlauf.json": json.dumps(
                [_watch("vid1")]
            ),
            "Takeout/YouTube und YouTube Music/Verlauf/Suchverlauf.json": json.dumps(
                [
                    {
                        "header": "YouTube",
                        "title": "Gesucht nach: katzen",
                        "titleUrl": "https://www.youtube.com/results?search_query=katzen",
                        "time": "2026-01-01T00:00:00Z",
                        "products": ["YouTube"],
                    }
                ]
            ),
        }
    )
    ddp = YoutubeDdp(zf)
    assert len(ddp.entries) == 2
    assert ddp.sources == (
        "Takeout/YouTube und YouTube Music/Verlauf/Suchverlauf.json, "
        "Takeout/YouTube und YouTube Music/Verlauf/Wiedergabeverlauf.json"
    )


def test_ads_only_activity_still_produces_watch_rows():
    """An ad impression has no titleUrl, and is a watch row all the same."""
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_homepage_ad(f"2026-01-0{day}T00:00:00Z") for day in range(1, 5)]
            )
        }
    )
    df = extract_watch_history(zf)
    assert len(df) == 4
    assert set(df["Details"]) == {"Von Google Anzeigen"}
    assert set(df["Video ID"]) == {""}


def test_a_parsed_ddp_is_reused_rather_than_parsed_again():
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch("vid1")]
            )
        }
    )
    ddp = YoutubeDdp(zf)
    assert extract_watch_history(ddp) is not None
    # The ZIP has been consumed by now; a second behavior must still work.
    assert extract_subscriptions(ddp) is None
