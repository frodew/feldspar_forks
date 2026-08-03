from datetime import datetime

import pandas as pd

from port.extraction_helpers import cap_rows, find_activity_entries

# Marks a "My Activity" entry as a search (rather than a watch): the URL
# shape doesn't depend on the export language, unlike the file/folder names.
SEARCH_URL_MARKER = "/results?search_query="

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


def extract_search_history(zip_file_path, max_rows):
    """
    Extract YouTube search history from ZIP file.
    Returns complete list of search queries with search query text and timestamp.
    Sorted by time with newest on top.
    """

    # Find the search history file by structure, regardless of its
    # (localized) file/folder name
    entries = find_activity_entries(zip_file_path, SEARCH_URL_MARKER)

    if entries is None:
        return None, 0

    # Extract data from each entry
    search_data = []

    for entry in entries:
        title_url = entry.get("titleUrl", "")
        if SEARCH_URL_MARKER not in title_url:
            continue

        # Extract timestamp
        timestamp = entry.get("time", "")

        # Extract activity controls
        activity_controls = entry.get("activityControls", [])
        activity_controls_str = (
            ", ".join(activity_controls) if activity_controls else ""
        )

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
        return (
            pd.DataFrame(columns=["Timestamp", "Search Query", "Activity Controls"]),
            0,
        )

    # Create DataFrame
    df = pd.DataFrame(search_data)

    # Sort by timestamp (newest on top)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return cap_rows(df, max_rows)
