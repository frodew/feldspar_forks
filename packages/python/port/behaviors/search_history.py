from datetime import datetime

import pandas as pd

from port.extraction_helpers import extract_single_file_from_zip

# Patterns to find the relevant files for this behavior (English and German)
patterns = ["history/search-history", "Verlauf/Suchverlauf"]

# Title used in prompt_consent() to describe this behavior
title = {
    "en": "Search History",
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


def extract_search_history(zip_file_path):
    """
    Extract YouTube search history from ZIP file.
    Returns complete list of search queries with search query text and timestamp.
    Only includes entries where title starts with "Searched for" or "Gesucht nach:".
    Sorted by time with newest on top.
    """

    # Try to find the file using either English or German pattern
    search_history_json = None
    for pattern in patterns:
        search_history_json = extract_single_file_from_zip(zip_file_path, pattern)
        if search_history_json is not None:
            break

    if search_history_json is None:
        return None

    # Extract data from each entry
    search_data = []

    for entry in search_history_json:
        # Extract title
        title_text = entry.get("title", "")

        # Only include entries where title starts with "Searched for" or "Gesucht nach:"
        is_search = False
        search_query = ""

        if title_text.startswith("Searched for "):
            is_search = True
            search_query = title_text[13:]  # Keep everything after "Searched for "
        elif title_text.startswith("Gesucht nach: "):
            is_search = True
            search_query = title_text[14:]  # Keep everything after "Gesucht nach: "

        if not is_search:
            continue

        # Extract timestamp
        timestamp = entry.get("time", "")

        # Extract activity controls
        activity_controls = entry.get("activityControls", [])
        activity_controls_str = (
            ", ".join(activity_controls) if activity_controls else ""
        )

        search_data.append(
            {
                "Timestamp": format_timestamp(timestamp),
                "Search Query": search_query,
                "Activity Controls": activity_controls_str,
            }
        )

    if not search_data:
        return pd.DataFrame(columns=["Timestamp", "Search Query", "Activity Controls"])

    # Create DataFrame
    df = pd.DataFrame(search_data)

    # Sort by timestamp (newest on top)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return df
