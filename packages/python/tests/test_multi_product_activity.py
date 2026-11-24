"""Tests for reading YouTube activity out of a multi-product Takeout."""

import io
import json
import sys
import zipfile
from pathlib import Path

# Add packages/python to sys.path so the `port` package resolves.
sys.path.insert(0, str(Path(__file__).parent.parent))

from port.behaviors.search_history import extract_search_history
from port.behaviors.subscriptions import extract_subscriptions
from port.behaviors.watch_history import extract_watch_history


def _zip_of(files: dict[str, str]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf


def _watch(video_id, product="YouTube", details=False, time="2026-01-01T00:00:00Z"):
    entry = {
        "header": product,
        "title": f"Video {video_id} angesehen",
        "titleUrl": f"https://www.youtube.com/watch?v={video_id}",
        "time": time,
        "products": [product],
        "subtitles": [{"name": "Kanal", "url": "http://www.youtube.com/channel/UCabc"}],
        "activityControls": ["YouTube-Wiedergabeverlauf"],
    }
    if details:
        entry["details"] = [{"name": "Von Google Anzeigen"}]
    return entry


def _search(query, product="YouTube"):
    return {
        "header": product,
        "title": f"Gesucht nach: {query}",
        "titleUrl": f"https://www.youtube.com/results?search_query={query}",
        "time": "2026-01-01T00:00:00Z",
        "products": [product],
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


def test_watch_history_ignores_other_products_that_sort_first():
    """Bildersuche sorts before YouTube and carries /watch?v= URLs of its own."""
    zf = _zip_of(
        {
            "Meine Aktivitäten/Bildersuche/MeineAktivitäten.json": json.dumps(
                [_watch("img1", product="Bildersuche")]
            ),
            "Meine Aktivitäten/Chrome/MeineAktivitäten.json": json.dumps(
                [_watch("chr1", product="Chrome")]
            ),
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch(f"yt{i}") for i in range(5)]
            ),
        }
    )
    df = extract_watch_history(zf)
    assert len(df) == 5
    assert set(df["Video ID"]) == {f"yt{i}" for i in range(5)}


def test_search_history_ignores_other_products_that_sort_first():
    zf = _zip_of(
        {
            "Meine Aktivitäten/Chrome/MeineAktivitäten.json": json.dumps(
                [_search("chrome_query", product="Chrome")]
            ),
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_search("katzen"), _search("hunde")]
            ),
        }
    )
    df = extract_search_history(zf)
    assert len(df) == 2
    assert not any("chrome_query" in q for q in df["Search Query"])


def test_full_takeout_resolves_watch_and_search_from_separate_files():
    """A YouTube-DDP splits history across two files; both must resolve."""
    zf = _zip_of(
        {
            "YouTube und YouTube Music/Verlauf/Wiedergabeverlauf.json": json.dumps(
                [_watch(f"yt{i}") for i in range(9)]
            ),
            "YouTube und YouTube Music/Verlauf/Suchverlauf.json": json.dumps(
                [_search(f"q{i}") for i in range(3)]
            ),
        }
    )
    assert len(extract_watch_history(zf)) == 9
    assert len(extract_search_history(zf)) == 3


def test_watch_history_flags_google_ads_entries():
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch("organic1"), _watch("ad1", details=True), _watch("organic2")]
            )
        }
    )
    df = extract_watch_history(zf)
    # the exported text is kept verbatim; ordinary views stay blank
    details = dict(zip(df["Video ID"], df["Details"]))
    assert details == {"organic1": "", "ad1": "Von Google Anzeigen", "organic2": ""}


def test_activity_json_outside_youtube_folder_is_ignored():
    """Only YouTube folders are read, so unrelated products are never parsed."""
    zf = _zip_of(
        {
            "Meine Aktivitäten/Google Suche/MeineAktivitäten.json": json.dumps(
                # mislabelled as YouTube, but not in a YouTube folder
                [_watch("suche1"), _watch("suche2")]
            ),
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch("yt1")]
            ),
        }
    )
    df = extract_watch_history(zf)
    assert list(df["Video ID"]) == ["yt1"]


def test_subscriptions_found_without_any_watch_entries():
    """Watch history can be off while subscribe events are still exported."""
    zf = _zip_of(
        {
            "Meine Aktivitäten/Bildersuche/MeineAktivitäten.json": json.dumps(
                [_watch("img1", product="Bildersuche")]
            ),
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_channel_event("UCone"), _channel_event("UCtwo")]
            ),
        }
    )
    df = extract_subscriptions(zf)
    assert len(df) == 2
    assert set(df["Channel ID"]) == {"UCone", "UCtwo"}


def test_subscriptions_prefers_activity_events_over_the_csv_snapshot():
    """The event log is timestamped; the CSV is only a point-in-time list."""
    zf = _zip_of(
        {
            "YouTube und YouTube Music/Abos/Abos.csv": (
                "Kanal-ID,Kanal-URL,Kanaltitel\n"
                "UCcsv,http://www.youtube.com/channel/UCcsv,Aus CSV\n"
            ),
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_channel_event("UCevent")]
            ),
        }
    )
    df = extract_subscriptions(zf)
    assert list(df["Channel ID"]) == ["UCevent"]


def _entry(title, title_url, details=False, header="YouTube"):
    entry = {
        "header": header,
        "title": title,
        "titleUrl": title_url,
        "time": "2026-01-01T00:00:00Z",
        "products": ["YouTube"],
        "activityControls": ["YouTube-Wiedergabeverlauf"],
    }
    if details:
        entry["details"] = [{"name": "Von Google Anzeigen"}]
    return entry


def test_watch_history_keeps_clicks_posts_and_playlists_labelled_in_details():
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [
                    _watch("vid1"),
                    _watch("vid2", details=True),
                    _entry("https://ad.doubleclick.net/x aufgerufen",
                           "https://www.google.com/url?q=https://ad.doubleclick.net/x",
                           details=True),
                    _entry("ein Beitrag angesehen",
                           "https://www.youtube.com/post/UgkxPOST1"),
                    _entry("Gespeichert: Eine Playlist",
                           "https://www.youtube.com/playlist?list=PLabc"),
                    _entry("YouTube Shorts geteilt",
                           "https://youtube.com/shorts/SHORT1"),
                ]
            )
        }
    )
    df = extract_watch_history(zf)
    assert len(df) == 6
    kinds = sorted(df["Details"])
    assert kinds == [
        "",
        "Von Google Anzeigen",
        "Von Google Anzeigen, clicked ad",
        "community post",
        "playlist",
        "shorts",
    ]
    ids = dict(zip(df["Details"], df["Video ID"]))
    assert ids["community post"] == "UgkxPOST1"
    assert ids["playlist"] == "PLabc"
    assert ids["shorts"] == "SHORT1"
    assert ids["Von Google Anzeigen, clicked ad"] == ""


def test_watch_history_excludes_searches_and_subscribe_events():
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch("vid1"), _search("katzen"), _channel_event("UCone")]
            )
        }
    )
    df = extract_watch_history(zf)
    assert list(df["Video ID"]) == ["vid1"]


def test_header_is_always_folded_into_activity_controls():
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_watch("vid1"), _entry("Song angesehen",
                                        "https://www.youtube.com/watch?v=music1",
                                        header="YouTube Music")]
            )
        }
    )
    df = extract_watch_history(zf)
    controls = dict(zip(df["Video ID"], df["Activity Controls"]))
    # the default "YouTube" is kept too, not just the exceptions
    assert controls["vid1"] == "YouTube, YouTube-Wiedergabeverlauf"
    assert controls["music1"] == "YouTube Music, YouTube-Wiedergabeverlauf"


def test_search_history_also_carries_the_header():
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [
                    _search("katzen"),
                    {
                        "header": "YouTube Music",
                        "title": "Gesucht nach: jazz",
                        "titleUrl": "https://www.youtube.com/results?search_query=jazz",
                        "time": "2026-01-01T00:00:00Z",
                        "products": ["YouTube"],
                        "activityControls": ["YouTube-Suchverlauf"],
                    },
                ]
            )
        }
    )
    df = extract_search_history(zf)
    controls = dict(zip(df["Search Query"], df["Activity Controls"]))
    assert controls["Gesucht nach: katzen"] == "YouTube, YouTube-Suchverlauf"
    assert controls["Gesucht nach: jazz"] == "YouTube Music, YouTube-Suchverlauf"


def test_retention_countdown_moves_from_controls_to_details():
    """A dismissed shelf names no activity control, so that column must stay
    header-only - otherwise the countdown masks "no control named"."""
    zf = _zip_of(
        {
            "Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [
                    _watch("vid1"),
                    {
                        "header": "YouTube",
                        "title": "Dismissed shelf",
                        "description": "Expiration date: Nov 2, 2026",
                        "time": "2026-01-01T00:00:00Z",
                        "products": ["YouTube"],
                    },
                ]
            )
        }
    )
    df = extract_watch_history(zf)
    shelf = df[df["Video Title"] == "Dismissed shelf"].iloc[0]
    assert shelf["Activity Controls"] == "YouTube"
    assert shelf["Details"] == "Expiration date: Nov 2, 2026"
    # a row that does name a control keeps its description out of Details
    ordinary = df[df["Video ID"] == "vid1"].iloc[0]
    assert ordinary["Details"] == ""


def test_subscriptions_ignores_csvs_outside_youtube_folders():
    """Only YouTube folders are read, for CSVs as well as activity JSON."""
    zf = _zip_of(
        {
            "Takeout/Drive/Kanalliste.csv": (
                "A,B,C\nUCstray,http://www.youtube.com/channel/UCstray,Fremd\n"
            ),
            "Takeout/Meine Aktivitäten/YouTube/MeineAktivitäten.json": json.dumps(
                [_channel_event("UCevent")]
            ),
        }
    )
    df = extract_subscriptions(zf)
    assert list(df["Channel ID"]) == ["UCevent"]
