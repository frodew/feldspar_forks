from port.extraction_helpers import epoch_to_date, extract_multiple_files_from_zip
import pandas as pd
from datetime import datetime

# Patterns to find the relevant files for this behavior (two files needed)
patterns = ["posts_viewed", "videos_watched"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie waren Sie pro Tag auf Instagram? [pro Tag]",
}


def extract_session_count(zip_file_path):
    """
    Calculate the total number of Instagram sessions per day.
    A session continues if the time between views is less than 180 seconds.
    Sessions reset at midnight.

    Works with either posts_viewed, videos_watched, or both.
    """

    # Extract data from ZIP file
    combined_data = extract_multiple_files_from_zip(zip_file_path, patterns)

    if combined_data is None:
        return None

    # Constants
    SESSION_BREAK_THRESHOLD = 180  # seconds

    # Extract data from the combined format
    posts_viewed_json = combined_data.get("posts_viewed", {})
    videos_watched_json = combined_data.get("videos_watched", {})

    # Get timestamps from post views (if available)
    post_timestamps = []
    if posts_viewed_json:
        post_timestamps = [
            entry["string_map_data"]["Time"]["timestamp"]
            for entry in posts_viewed_json.get("impressions_history_posts_seen", [])
            if "Time" in entry["string_map_data"]
        ]

    # Get timestamps from video views (if available)
    video_timestamps = []
    if videos_watched_json:
        video_timestamps = [
            entry["string_map_data"]["Time"]["timestamp"]
            for entry in videos_watched_json.get(
                "impressions_history_videos_watched", []
            )
            if "Time" in entry["string_map_data"]
        ]

    # Combine and sort all timestamps
    all_timestamps = sorted(post_timestamps + video_timestamps)

    if not all_timestamps:
        return pd.DataFrame(columns=["Datum", "Anzahl Sitzungen"])

    # Calculate session count per day
    from datetime import datetime

    daily_session_count = {}
    daily_first_timestamp = {}  # Store first timestamp for each day
    last_time = None
    current_day = None

    for ts in all_timestamps:
        current_time = datetime.fromtimestamp(ts)
        new_day = current_time.date()

        # Initialize the day in our dictionary if needed
        if new_day not in daily_session_count:
            daily_session_count[new_day] = 0
            daily_first_timestamp[new_day] = ts  # Store first timestamp for this day

        # Check if we're starting a new session
        start_new_session = False

        if last_time is None:
            # First activity - start first session
            start_new_session = True
        elif new_day != current_day:
            # Day changed - start new session
            start_new_session = True
        elif (current_time - last_time).total_seconds() > SESSION_BREAK_THRESHOLD:
            # More than threshold time since last activity - start new session
            start_new_session = True

        if start_new_session:
            daily_session_count[new_day] += 1

        # Update for the next iteration
        last_time = current_time
        current_day = new_day

    # Convert to DataFrame
    dates = [
        epoch_to_date(daily_first_timestamp[d])
        for d in daily_session_count.keys()
    ]
    session_counts = list(daily_session_count.values())

    result_df = pd.DataFrame({"Datum": dates, "Anzahl Sitzungen": session_counts})
    result_df = result_df.sort_values(by="Datum").reset_index(drop=True)

    return result_df
