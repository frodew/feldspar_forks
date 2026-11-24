"""Tests for reading activity HTML exports into JSON-shaped entry dicts."""

import sys
from pathlib import Path

import pytest

# Add packages/python to sys.path so the `port` package resolves.
sys.path.insert(0, str(Path(__file__).parent.parent))

from port.html_activity import parse_activity_html, to_iso_utc
from tests.html_fixtures import (
    activity_cell,
    activity_html,
    searched_cell,
    subscribed_cell,
    watched_cell,
)


def test_watch_cell_matches_the_json_entry_shape():
    (entry,) = parse_activity_html(activity_html(watched_cell("vid1")))
    assert entry == {
        "header": "YouTube",
        "title": "Ein Video angesehen",
        "titleUrl": "https://www.youtube.com/watch?v=vid1",
        "subtitles": [
            {"name": "Ein Kanal", "url": "https://www.youtube.com/channel/UCabc"}
        ],
        "time": "2026-11-17T08:00:38Z",
        "products": ["YouTube"],
        "activityControls": ["YouTube-Wiedergabeverlauf"],
    }


def test_search_cell_keeps_the_localized_verb_and_the_query_url():
    (entry,) = parse_activity_html(activity_html(searched_cell("katzen")))
    assert entry["title"] == "Gesucht nach: katzen"
    assert entry["titleUrl"].endswith("/results?search_query=katzen")
    assert entry["activityControls"] == ["YouTube-Suchverlauf"]


def test_subscribe_cell_has_a_channel_url_and_names_no_control():
    """No activity control is the structural mark of a channel event."""
    (entry,) = parse_activity_html(activity_html(subscribed_cell("UCone")))
    assert entry["titleUrl"] == "https://www.youtube.com/channel/UCone"
    assert entry["title"] == "Ein Kanal abonniert"
    assert "activityControls" not in entry
    assert "subtitles" not in entry


def test_cells_parse_independently_of_each_other():
    entries = parse_activity_html(
        activity_html(watched_cell("vid1"), searched_cell("hunde"), subscribed_cell("UCone"))
    )
    assert [entry["titleUrl"] for entry in entries] == [
        "https://www.youtube.com/watch?v=vid1",
        "https://www.youtube.com/results?search_query=hunde",
        "https://www.youtube.com/channel/UCone",
    ]


def test_ad_details_are_kept_verbatim():
    (entry,) = parse_activity_html(
        activity_html(watched_cell("vid1", details=("Von Google Anzeigen",)))
    )
    assert entry["details"] == [{"name": "Von Google Anzeigen"}]


def test_entry_without_details_has_no_details_key():
    """Only accounts with personalized ads on ever carry a Details section."""
    (entry,) = parse_activity_html(activity_html(watched_cell("vid1")))
    assert "details" not in entry


def test_retention_countdown_is_read_as_the_description():
    (entry,) = parse_activity_html(
        activity_html(
            activity_cell(
                "Ausgeblendeter Bereich",
                "06.05.2026, 09:23:46 MESZ",
                description="Ablaufdatum: 02.11.2026",
            )
        )
    )
    assert entry["description"] == "Ablaufdatum: 02.11.2026"
    assert entry["time"] == "2026-05-06T07:23:46Z"
    assert "titleUrl" not in entry
    assert "activityControls" not in entry


def test_several_controls_are_split_on_the_comma():
    (entry,) = parse_activity_html(
        activity_html(
            watched_cell(
                "vid1",
                controls=("Web- &amp; App-Aktivitäten", "YouTube-Wiedergabeverlauf"),
            )
        )
    )
    assert entry["activityControls"] == [
        "Web- & App-Aktivitäten",
        "YouTube-Wiedergabeverlauf",
    ]


def test_entities_in_titles_are_unescaped():
    (entry,) = parse_activity_html(
        activity_html(watched_cell("vid1", title="OLED &quot;iPad&quot; &amp; Co"))
    )
    assert entry["title"] == 'OLED "iPad" & Co angesehen'


def test_the_no_break_space_after_the_verb_reads_as_a_plain_space():
    """Google writes "Gesucht nach:&nbsp;X" where the JSON has a plain space."""
    (entry,) = parse_activity_html(activity_html(searched_cell("katzen")))
    assert entry["title"] == "Gesucht nach: katzen"


def test_trailing_spaces_in_a_value_are_kept():
    """A query searched as "trump biden " carries that space in the JSON too."""
    (entry,) = parse_activity_html(
        activity_html(
            activity_cell(
                'Gesucht nach:&nbsp;<a href="https://www.youtube.com/results?search_query=trump+biden+">trump biden </a>',
                "16.10.2020, 10:55:03 MESZ",
            )
        )
    )
    assert entry["title"] == "Gesucht nach: trump biden "


def test_products_section_is_read_for_the_youtube_filter():
    (entry,) = parse_activity_html(
        activity_html(activity_cell("Etwas", "17.11.2026, 09:00:38 MEZ", products=("Chrome",)))
    )
    assert entry["products"] == ["Chrome"]


def test_sub_product_rides_in_the_header():
    (entry,) = parse_activity_html(
        activity_html(watched_cell("music1", header="YouTube Music"))
    )
    assert entry["header"] == "YouTube Music"


def test_an_empty_document_yields_no_entries():
    assert parse_activity_html("<html><body></body></html>") == []


@pytest.mark.parametrize(
    "rendered,expected",
    [
        # German: numeric date, winter and summer offsets
        ("17.11.2026, 09:00:38 MEZ", "2026-11-17T08:00:38Z"),
        ("07.05.2026, 00:44:26 MESZ", "2026-05-06T22:44:26Z"),
        # English: month first, 12-hour clock, narrow no-break space before PM
        ("Nov 11, 2026, 1:10:38 PM CET", "2026-11-11T12:10:38Z"),
        ("Nov 17, 2026, 9:00:38 AM CET", "2026-11-17T08:00:38Z"),
        ("Jan 1, 2026, 12:30:00 AM CET", "2025-12-31T23:30:00Z"),
        ("Jan 1, 2026, 12:30:00 PM CET", "2026-01-01T11:30:00Z"),
        # Turkish: day first, localized month abbreviation, no comma
        ("17 Kas 2026 09:00:38 CET", "2026-11-17T08:00:38Z"),
        ("20 Eki 2026 17:30:15 CET", "2026-10-20T16:30:15Z"),
        # Italian, Polish, Ukrainian abbreviations
        ("17 nov 2026, 09:00:38 CET", "2026-11-17T08:00:38Z"),
        ("17 lis 2026, 09:00:38 CET", "2026-11-17T08:00:38Z"),
        ("17 лист. 2026 р., 09:00:38 CET", "2026-11-17T08:00:38Z"),
    ],
)
def test_timestamps_convert_to_utc(rendered, expected):
    assert to_iso_utc(rendered) == expected


@pytest.mark.parametrize(
    "rendered",
    [
        "17.11.2026, 09:00:38 XYZ",  # unknown timezone
        "17 Qqq 2026 09:00:38 CET",  # unknown month name
        "irgendwann letztes Jahr",  # no clock at all
    ],
)
def test_unreadable_timestamps_are_kept_as_exported(rendered):
    """Losing the UTC instant is acceptable; losing the row is not."""
    assert to_iso_utc(rendered) == rendered
