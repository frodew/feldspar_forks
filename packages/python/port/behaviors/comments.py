from datetime import datetime

import pandas as pd

from port.extraction_helpers import find_csv_by_shape

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Kommentare",
}


def is_comments_csv(df):
    """
    The comments CSV always has 6 columns: Comment ID, Channel ID, Timestamp,
    Price, Video ID, Comment Text (in that order, regardless of locale). The
    comment text is stored as a JSON blob (e.g. {"text": "..."}), which
    reliably tells this file apart from other 6-column files.
    """
    return df.iloc[:, 5].astype(str).str.contains('{"text"', regex=False).any()


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


def extract_comments(zip_file_path):
    """
    Extract YouTube comments from ZIP file.
    Returns complete list of comments with Channel ID, Video ID, and Timestamp.
    Sorted by time with newest on top.
    """

    comments_csv = find_csv_by_shape(zip_file_path, 6, is_comments_csv)

    if comments_csv is None:
        return None

    # Create output DataFrame with formatted timestamps (columns addressed by
    # position, since the column headers are localized)
    df = pd.DataFrame(
        {
            "Timestamp": comments_csv.iloc[:, 2].apply(format_timestamp),
            "Video ID": comments_csv.iloc[:, 4],
            "Channel ID": comments_csv.iloc[:, 1],
        }
    )

    # Sort by timestamp (newest on top)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return df
