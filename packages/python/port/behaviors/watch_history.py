from datetime import datetime

import pandas as pd

from port.extraction_helpers import find_activity_entries

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


def extract_watch_history(file):
    """
    Extract YouTube watch history from ZIP file.
    Returns complete list of watched videos with Video ID, Channel ID, Channel name, and Timestamp.
    Sorted by time with newest on top.
    """

    # Find the watch history file by structure, regardless of its (localized)
    # file/folder name
    entries = find_activity_entries(file, WATCH_URL_MARKER)

    if entries is None:
        return None

    # Extract data from each entry
    video_data = []

    for entry in entries:
        title_url = entry.get("titleUrl", "")
        if title_url and WATCH_URL_MARKER not in title_url:
            continue

        # Entries with no titleUrl at all are watch-shaped placeholders
        # Google didn't attach a video to: either a redacted "hidden
        # section" or a since-deleted video. They carry no video/channel
        # info to extract, but are kept here (instead of dropped) so the
        # data isn't silently lost - they can be filtered back out later.

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

        # Extract activity controls. Hidden-section entries never have
        # activityControls, but some carry a "description" with a retention
        # countdown (e.g. "Ablaufdatum: 02.11.2026") - stash that in the same
        # column instead of adding a column that's empty for ~all other rows.
        activity_controls = entry.get("activityControls", [])
        if activity_controls:
            activity_controls_str = ", ".join(activity_controls)
        else:
            activity_controls_str = entry.get("description", "")

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
        return pd.DataFrame(
            columns=[
                "Timestamp",
                "Video Title",
                "Video ID",
                "Channel Name",
                "Channel ID",
                "Activity Controls",
            ]
        )

    # Create DataFrame
    df = pd.DataFrame(video_data)

    # Sort by timestamp (newest on top)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return df
