from datetime import datetime

import pandas as pd

from port.extraction_helpers import (
    SEARCH_URL_MARKER,
    activity_controls_with_header,
    find_activity_entries,
    title_url_contains,
    with_source,
)

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Suchverlauf",
}


def format_timestamp(timestamp_str):
    """Convert ISO timestamp to readable format: YYYY-MM-DD HH:MM:SS.mmm"""
    try:
        if not timestamp_str:
            return ""
        # Parse ISO format and convert to readable format
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[
            :-3
        ]  # Remove last 3 digits of microseconds
    except:
        return timestamp_str


def extract_search_history(file):
    """
    Extract YouTube search history from ZIP file.
    Returns complete list of search queries with search query text and timestamp.
    Sorted by time with newest on top.
    """

    # Find the search history file by structure, regardless of its
    # (localized) file/folder name
    entries, source = find_activity_entries(file, title_url_contains(SEARCH_URL_MARKER))

    if entries is None:
        return None

    # Extract data from each entry
    search_data = []

    for entry in entries:
        title_url = entry.get("titleUrl", "")
        if SEARCH_URL_MARKER not in title_url:
            continue

        # Extract timestamp
        timestamp = entry.get("time", "")

        activity_controls_str = activity_controls_with_header(entry)

        # Search query is kept as exported (e.g. "Searched for X" or
        # "Gesucht nach: X"): the verb is placed differently in every
        # language, so there's no reliable way to strip it without
        # hardcoding each language's grammar
        search_data.append(
            {
                "Timestamp": format_timestamp(timestamp),
                "Search Query": entry.get("title", ""),
                "Activity Controls": activity_controls_str,
            }
        )

    if not search_data:
        return with_source(
            pd.DataFrame(columns=["Timestamp", "Search Query", "Activity Controls"]),
            source,
        )

    # Create DataFrame
    df = pd.DataFrame(search_data)

    # Sort by timestamp (newest on top)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return with_source(df, source)
