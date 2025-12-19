import zipfile
from datetime import datetime
from io import StringIO

import pandas as pd

# Patterns to find the relevant files for this behavior (English and German)
patterns = ["comments/comments.csv", "Kommentare/Kommentare.csv"]

# Title used in prompt_consent() to describe this behavior
title = {
    "en": "Comments",
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


def extract_comments(zip_file_path):
    """
    Extract YouTube comments from ZIP file.
    Returns complete list of comments with Channel ID, Video ID, and Timestamp.
    Sorted by time with newest on top.
    """

    # Try to find the CSV file using either English or German pattern
    comments_csv = None

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            file_names = zip_ref.namelist()

            # Find the comments CSV file
            for pattern in patterns:
                for file_name in file_names:
                    if pattern in file_name and file_name.endswith(".csv"):
                        try:
                            with zip_ref.open(file_name) as csv_file:
                                csv_content = csv_file.read().decode("utf-8")
                                comments_csv = pd.read_csv(StringIO(csv_content))
                                break
                        except Exception as e:
                            print(f"Error reading comments CSV {file_name}: {e}")

                if comments_csv is not None:
                    break

    except Exception as e:
        print(f"Error extracting comments from ZIP: {e}")
        return None

    if comments_csv is None or comments_csv.empty:
        return None

    # Identify column names (check exact German column names from the file)
    channel_id_col = None
    video_id_col = None
    timestamp_col = None

    # Check for exact column names first (German)
    if "Kanal-ID" in comments_csv.columns:
        channel_id_col = "Kanal-ID"
    if "Video-ID" in comments_csv.columns:
        video_id_col = "Video-ID"
    if "Zeitstempel der Erstellung des Kommentars" in comments_csv.columns:
        timestamp_col = "Zeitstempel der Erstellung des Kommentars"

    # If not found, try English column names
    if channel_id_col is None:
        for col in comments_csv.columns:
            if "Channel ID" in col or "Channel Id" in col:
                channel_id_col = col
                break

    if video_id_col is None:
        for col in comments_csv.columns:
            if "Video ID" in col or "Video Id" in col:
                video_id_col = col
                break

    if timestamp_col is None:
        for col in comments_csv.columns:
            if "Timestamp" in col and "Create" in col:
                timestamp_col = col
                break

    if channel_id_col is None or video_id_col is None or timestamp_col is None:
        return pd.DataFrame(columns=["Timestamp", "Video ID", "Channel ID"])

    # Create output DataFrame with formatted timestamps
    df = pd.DataFrame(
        {
            "Timestamp": comments_csv[timestamp_col].apply(format_timestamp),
            "Video ID": comments_csv[video_id_col],
            "Channel ID": comments_csv[channel_id_col],
        }
    )

    # Sort by timestamp (newest on top)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return df
