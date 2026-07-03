from datetime import datetime

import pandas as pd

from port.extraction_helpers import extract_single_file_from_zip

# Patterns to find the relevant files for this behavior (English and German)
patterns = ["history/watch-history", "Verlauf/Wiedergabeverlauf"]

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


def extract_watch_history(zip_file_path):
    """
    Extract YouTube watch history from ZIP file.
    Returns complete list of watched videos with Video ID, Channel ID, Channel name, and Timestamp.
    Sorted by time with newest on top.
    """

    # Try to find the file using either English or German pattern
    watch_history_json = None
    for pattern in patterns:
        watch_history_json = extract_single_file_from_zip(zip_file_path, pattern)
        if watch_history_json is not None:
            break

    if watch_history_json is None:
        return None

    # Extract data from each entry
    video_data = []

    for entry in watch_history_json:
        # Only include actual video watches (entries with titleUrl)
        if "titleUrl" in entry and entry.get("titleUrl"):
            # Extract video ID from URL (format: https://www.youtube.com/watch?v=VIDEO_ID)
            video_id = None
            title_url = entry.get("titleUrl", "")
            if "watch?v=" in title_url:
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

            # Extract video title (remove "Watched " or "Angesehen " prefix if present)
            video_title = entry.get("title", "")
            if video_title.startswith("Watched "):
                video_title = video_title[8:]
            elif video_title.startswith("Angesehen "):  # German
                video_title = video_title[10:]

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
