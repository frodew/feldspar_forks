from datetime import datetime

import pandas as pd

from port.extraction_helpers import cap_rows, find_activity_entries

# Marks a "My Activity" entry as a watch (rather than a search): the URL
# shape doesn't depend on the export language, unlike the file/folder names.
WATCH_URL_MARKER = "/watch?v="

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wiedergabeverlauf",
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


def extract_watch_history(zip_file_path, max_rows):
    """
    Extract YouTube watch history from ZIP file.
    Returns complete list of watched videos with Video ID, Channel ID, Channel name, and Timestamp.
    Sorted by time with newest on top.
    """

    # Find the watch history file by structure, regardless of its (localized)
    # file/folder name
    entries = find_activity_entries(zip_file_path, WATCH_URL_MARKER)

    if entries is None:
        return None, 0

    # Extract data from each entry
    video_data = []

    for entry in entries:
        title_url = entry.get("titleUrl", "")
        if WATCH_URL_MARKER not in title_url:
            continue

        # Extract video ID from URL (format: https://www.youtube.com/watch?v=VIDEO_ID)
        video_id = title_url.split("watch?v=")[-1].split("&")[0]

        # Extract channel information from subtitles if available
        channel_id = None
        channel_name = None

        if "subtitles" in entry and len(entry["subtitles"]) > 0:
            subtitle = entry["subtitles"][0]
            if "url" in subtitle:
                channel_url = subtitle["url"]
                # Extract channel ID from URL (format: http://www.youtube.com/channel/CHANNEL_ID)
                if "/channel/" in channel_url:
                    channel_id = channel_url.split("/channel/")[-1]
            if "name" in subtitle:
                channel_name = subtitle["name"]

        # Extract timestamp
        timestamp = entry.get("time", "")

        # Extract activity controls
        activity_controls = entry.get("activityControls", [])
        activity_controls_str = (
            ", ".join(activity_controls) if activity_controls else ""
        )

        # Video title is kept as exported (e.g. "Watched X" or "X angesehen"):
        # the verb is placed differently in every language, so there's no
        # reliable way to strip it without hardcoding each language's grammar
        video_title = entry.get("title", "")

        video_data.append(
            {
                "Timestamp": format_timestamp(timestamp),
                "Video Title": video_title,
                "Video ID": video_id if video_id else "",
                "Channel Name": channel_name if channel_name else "",
                "Channel ID": channel_id if channel_id else "",
                "Activity Controls": activity_controls_str,
            }
        )

    if not video_data:
        return (
            pd.DataFrame(
                columns=[
                    "Timestamp",
                    "Video Title",
                    "Video ID",
                    "Channel Name",
                    "Channel ID",
                    "Activity Controls",
                ]
            ),
            0,
        )

    # Create DataFrame
    df = pd.DataFrame(video_data)

    # Sort by timestamp (newest on top)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return cap_rows(df, max_rows)
