from port.extraction_helpers import epoch_to_date, extract_multiple_files_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["post_comments_1", "reels_comments", "hype"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Posts, Reels und Stories kommentiert? [pro Tag]",
}

def extract_post_comments(post_comments_json):
    """extract your_instagram_activity/comments/post_comments_1 -> count per day"""

    # file can just be dict and not list if only one posted comment
    if isinstance(post_comments_json, dict):
        dates = [
            epoch_to_date(post_comments_json["string_map_data"]["Time"]["timestamp"])
        ]
    else:
        dates = [
            epoch_to_date(t["string_map_data"]["Time"]["timestamp"])
            for t in post_comments_json
        ]  # get list with timestamps in epoch format

    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_reel_comments(reel_comments_json):
    """extract your_instagram_activity/comments/reels_comments -> count per day"""

    dates = [
        epoch_to_date(t["string_map_data"]["Time"]["timestamp"])
        for t in reel_comments_json["comments_reels_comments"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_story_comments(story_comments_json):
    """extract your_instagram_activity/comments/story_comments -> count per day"""

    dates = [
        epoch_to_date(t["string_map_data"]["Time"]["timestamp"])
        for t in story_comments_json["comments_story_comments"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_post_and_reel_comments(zip_file_path):
    """Extract and combine post comments, reel comments, and story comments from ZIP file"""

    # Map file patterns to expected keys in the data structure
    key_mapping = {
        "post_comments_1": "post_comments",
        "reels_comments": "reel_comments",
        "hype": "story_comments"
    }

    # Extract data from ZIP file
    combined_data = extract_multiple_files_from_zip(zip_file_path, patterns, key_mapping)

    if combined_data is None:
        return None

    # Initialize an empty DataFrame to store the combined results
    combined_df = pd.DataFrame(columns=["Datum", "Anzahl"])

    # Extract post comments if available
    post_comments_data = combined_data.get("post_comments", {})
    if post_comments_data:
        post_comments_df = extract_post_comments(post_comments_data)
        if not post_comments_df.empty:
            combined_df = post_comments_df.rename(columns={post_comments_df.columns[1]: "Anzahl"})

    # Extract reel comments if available
    reel_comments_data = combined_data.get("reel_comments", {})
    if reel_comments_data:
        reel_comments_df = extract_reel_comments(reel_comments_data)
        if not reel_comments_df.empty:
            if not combined_df.empty:
                reel_comments_df = reel_comments_df.rename(columns={reel_comments_df.columns[1]: "Anzahl"})
                combined_df = pd.merge(combined_df, reel_comments_df, on="Datum", how='outer', suffixes=('_post', '_reel'))
                combined_df["Anzahl"] = combined_df.filter(like="Anzahl").sum(axis=1, skipna=True).fillna(0).astype(int)
                combined_df = combined_df[["Datum", "Anzahl"]]
            else:
                combined_df = reel_comments_df.rename(columns={reel_comments_df.columns[1]: "Anzahl"})

    # Extract story comments if available
    story_comments_data = combined_data.get("story_comments", {})
    if story_comments_data:
        story_comments_df = extract_story_comments(story_comments_data)
        if not story_comments_df.empty:
            if not combined_df.empty:
                story_comments_df = story_comments_df.rename(columns={story_comments_df.columns[1]: "Anzahl"})
                combined_df = pd.merge(combined_df, story_comments_df, on="Datum", how='outer', suffixes=('', '_story'))
                combined_df["Anzahl"] = combined_df.filter(like="Anzahl").sum(axis=1, skipna=True).fillna(0).astype(int)
                combined_df = combined_df[["Datum", "Anzahl"]]
            else:
                combined_df = story_comments_df.rename(columns={story_comments_df.columns[1]: "Anzahl"})

    if not combined_df.empty:
        combined_df = combined_df.sort_values(by="Datum").reset_index(drop=True)

    return combined_df
