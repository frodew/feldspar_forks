from port.extraction_helpers import epoch_to_date, extract_multiple_files_from_zip
import pandas as pd
from datetime import datetime

# Patterns to find the relevant files for this behavior (two files needed)
patterns = ["posts_viewed", "videos_watched"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie viel Zeit haben Sie auf Instagram verbracht? [Sekunden pro Tag]",
}




def extract_time_spent(zip_file_path):
    """
    Calculate the total time spent on Instagram per day.
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
    DEFAULT_ACTIVITY_TIME = 20  # seconds for the last activity in a session

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
        return pd.DataFrame(columns=["Datum", "Verbrachte Zeit (Sekunden)"])

    # Calculate time spent per day
    from datetime import datetime

    daily_time_spent = {}
    session_start_time = None
    last_time = None
    current_day = None

    for ts in all_timestamps:
        current_time = datetime.fromtimestamp(ts)
        new_day = current_time.date()

        # Initialize the day in our dictionary if needed
        if new_day not in daily_time_spent:
            daily_time_spent[new_day] = 0

        # Check if we're starting a new session
        start_new_session = False

        if last_time is None:
            # First activity
            start_new_session = True
        elif new_day != current_day:
            # Day changed, end previous session and start new one
            if session_start_time:
                session_time = (
                    last_time - session_start_time
                ).total_seconds() + DEFAULT_ACTIVITY_TIME
                daily_time_spent[current_day] += session_time
            start_new_session = True
        elif (current_time - last_time).total_seconds() > SESSION_BREAK_THRESHOLD:
            # More than threshold time since last activity, end session and start new
            if session_start_time:
                session_time = (
                    last_time - session_start_time
                ).total_seconds() + DEFAULT_ACTIVITY_TIME
                daily_time_spent[current_day] += session_time
            start_new_session = True

        if start_new_session:
            session_start_time = current_time

        # Update for the next iteration
        last_time = current_time
        current_day = new_day

    # Handle the last session
    if session_start_time and last_time:
        session_time = (
            last_time - session_start_time
        ).total_seconds() + DEFAULT_ACTIVITY_TIME
        daily_time_spent[current_day] += session_time

    # Convert to DataFrame
    dates = [
        epoch_to_date(int(datetime(d.year, d.month, d.day).timestamp()))
        for d in daily_time_spent.keys()
    ]
    times = [round(t) for t in daily_time_spent.values()]  # Round to whole seconds

    result_df = pd.DataFrame({"Datum": dates, "Verbrachte Zeit (Sekunden)": times})
    result_df = result_df.sort_values(by="Datum").reset_index(drop=True)

    return result_df
