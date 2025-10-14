from port.extraction_helpers import epoch_to_date, extract_multiple_files_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["posts_viewed", "videos_watched"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie viele Posts und Videos haben Sie gesehen? [pro Tag]",
}


def extract_posts_seen(posts_seen_json):
    """extract ads_information/ads_and_topics/posts_viewed -> count per day"""

    timestamps = [
        t["string_map_data"]["Time"]["timestamp"]
        for t in posts_seen_json["impressions_history_posts_seen"]
    ]  # get list with timestamps in epoch format
    dates = [epoch_to_date(t) for t in timestamps]  # convert epochs to dates
    postViewedDates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = postViewedDates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_videos_seen(videos_seen_json):
    """extract ads_information/ads_and_topics/videos_watched -> count per day"""

    timestamps = [
        t["string_map_data"]["Time"]["timestamp"]
        for t in videos_seen_json["impressions_history_videos_watched"]
    ]  # get list with timestamps in epoch format
    dates = [epoch_to_date(t) for t in timestamps]  # convert epochs to dates
    videosViewedDates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = videosViewedDates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_posts_and_videos_seen(zip_file_path):
    """Extract and combine posts viewed and videos watched from ZIP file"""

    # Extract data from ZIP file
    combined_data = extract_multiple_files_from_zip(zip_file_path, patterns)

    if combined_data is None:
        return None

    # Initialize an empty DataFrame to store the combined results
    combined_df = pd.DataFrame(columns=["Datum", "Anzahl"])

    # Extract posts viewed if available
    posts_data = combined_data.get("posts_viewed", {})
    if posts_data:
        posts_df = extract_posts_seen(posts_data)
        if not posts_df.empty:
            combined_df = posts_df.rename(columns={posts_df.columns[1]: "Anzahl"})

    # Extract videos watched if available
    videos_data = combined_data.get("videos_watched", {})
    if videos_data:
        videos_df = extract_videos_seen(videos_data)
        if not videos_df.empty:
            # If we already have posts data, merge with videos data
            if not combined_df.empty:
                videos_df = videos_df.rename(columns={videos_df.columns[1]: "Anzahl"})
                # Merge on date and sum the counts
                combined_df = pd.merge(
                    combined_df,
                    videos_df,
                    on="Datum",
                    how="outer",
                    suffixes=("_posts", "_videos"),
                )
                combined_df["Anzahl"] = (
                    combined_df.filter(like="Anzahl")
                    .sum(axis=1, skipna=True)
                    .fillna(0)
                    .astype(int)
                )
                combined_df = combined_df[["Datum", "Anzahl"]]
            else:
                combined_df = videos_df.rename(columns={videos_df.columns[1]: "Anzahl"})

    # Sort by date
    if not combined_df.empty:
        combined_df = combined_df.sort_values(by="Datum").reset_index(drop=True)

    return combined_df
