"""Tests for recording which ZIP member each donated table came from."""

import io
import json
import sys
import zipfile
from pathlib import Path

# Add packages/python to sys.path so the `port` package resolves.
sys.path.insert(0, str(Path(__file__).parent.parent))

from port.behaviors.comments import extract_comments
from port.behaviors.search_history import extract_search_history
from port.behaviors.subscriptions import extract_subscriptions
from port.behaviors.watch_history import extract_watch_history
from port.script import add_source_metadata, extract_behavior

MY_ACTIVITY_DDP = "Takeout/Meine Aktivitäten/YouTube/MeineAktivitäten.json"
YOUTUBE_DDP_WATCH = "Takeout/YouTube und YouTube Music/Verlauf/Wiedergabeverlauf.json"
YOUTUBE_DDP_SUBS = "Takeout/YouTube und YouTube Music/Abos/Abos.csv"
YOUTUBE_DDP_COMMENTS = "Takeout/YouTube und YouTube Music/Kommentare/Kommentare.csv"


def _zip_of(files: dict[str, str]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf


def _watch(video_id):
    return {
        "header": "YouTube",
        "title": f"Video {video_id} angesehen",
        "titleUrl": f"https://www.youtube.com/watch?v={video_id}",
        "time": "2026-01-01T00:00:00Z",
        "products": ["YouTube"],
        "activityControls": ["YouTube-Wiedergabeverlauf"],
    }


def _search(query):
    return {
        "header": "YouTube",
        "title": f"Gesucht nach: {query}",
        "titleUrl": f"https://www.youtube.com/results?search_query={query}",
        "time": "2026-01-01T00:00:00Z",
        "products": ["YouTube"],
        "activityControls": ["YouTube-Suchverlauf"],
    }


def _channel_event(channel_id):
    return {
        "header": "YouTube",
        "title": f"Kanal {channel_id} abonniert",
        "titleUrl": f"https://www.youtube.com/channel/{channel_id}",
        "time": "2026-01-01T00:00:00Z",
        "products": ["YouTube"],
    }


SUBS_CSV = (
    "Kanal-ID,Kanal-URL,Kanaltitel\n"
    "UCcsv,http://www.youtube.com/channel/UCcsv,Aus CSV\n"
)
COMMENTS_CSV = (
    "Kommentar-ID,Kanal-ID,Erstellungszeitstempel,Preis,Video-ID,Kommentartext\n"
    'Ugxabc,UCabc,2026-01-01T00:00:00Z,,vid1,"{""text"": ""hallo""}"\n'
)


def test_my_activity_ddp_tables_name_the_activity_file():
    zf = _zip_of(
        {
            MY_ACTIVITY_DDP: json.dumps(
                [_watch("vid1"), _search("katzen"), _channel_event("UCone")]
            )
        }
    )
    assert extract_watch_history(zf).attrs["source"] == MY_ACTIVITY_DDP
    assert extract_search_history(zf).attrs["source"] == MY_ACTIVITY_DDP
    assert extract_subscriptions(zf).attrs["source"] == MY_ACTIVITY_DDP


def test_youtube_ddp_tables_name_their_own_files():
    """The CSV sources are the giveaway that this is a YouTube-DDP."""
    zf = _zip_of(
        {
            YOUTUBE_DDP_WATCH: json.dumps([_watch("vid1")]),
            YOUTUBE_DDP_SUBS: SUBS_CSV,
            YOUTUBE_DDP_COMMENTS: COMMENTS_CSV,
        }
    )
    assert extract_watch_history(zf).attrs["source"] == YOUTUBE_DDP_WATCH
    assert extract_subscriptions(zf).attrs["source"] == YOUTUBE_DDP_SUBS
    assert extract_comments(zf).attrs["source"] == YOUTUBE_DDP_COMMENTS


def test_subscriptions_source_shows_the_event_log_winning_over_the_csv():
    zf = _zip_of(
        {
            YOUTUBE_DDP_SUBS: SUBS_CSV,
            MY_ACTIVITY_DDP: json.dumps([_channel_event("UCevent")]),
        }
    )
    assert extract_subscriptions(zf).attrs["source"] == MY_ACTIVITY_DDP


def test_missing_behavior_file_leaves_the_source_empty():
    """No searches anywhere counts as missing, and names no source."""
    zf = _zip_of({MY_ACTIVITY_DDP: json.dumps([_watch("vid1")])})
    df = extract_behavior("search_history", zf)
    assert list(df.columns) == ["No Information"]
    assert df.attrs.get("source", "") == ""


def test_add_source_metadata_fills_in_each_table():
    data = {
        "watch_history": {"data": [], "metadata": {"deletedRowCount": 0}},
        "subscriptions": {"data": []},
    }
    add_source_metadata(
        data, {"watch_history": MY_ACTIVITY_DDP, "subscriptions": YOUTUBE_DDP_SUBS}
    )
    assert data["watch_history"]["metadata"] == {
        "deletedRowCount": 0,
        "source": MY_ACTIVITY_DDP,
    }
    assert data["subscriptions"]["metadata"] == {"source": YOUTUBE_DDP_SUBS}


def test_add_source_metadata_skips_tables_the_participant_did_not_return():
    data = {"watch_history": {"data": [], "metadata": {}}}
    add_source_metadata(data, {"watch_history": MY_ACTIVITY_DDP, "comments": ""})
    assert "comments" not in data
    assert data["watch_history"]["metadata"]["source"] == MY_ACTIVITY_DDP
