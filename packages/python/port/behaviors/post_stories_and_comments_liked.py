from port.extraction_helpers import epoch_to_date, extract_multiple_files_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["liked_posts", "story_likes", "liked_comments"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Posts, Stories oder Kommentare geliked? [pro Tag]",
}

def extract_posts_liked(posts_liked_json):
    """extract your_instagram_activity/likes/liked_posts -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in posts_liked_json["likes_media_likes"]
    ]
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_stories_liked(stories_liked_json):
    """extract your_instagram_activity/story_sticker_interactions/story_likes -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in stories_liked_json["story_activities_story_likes"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_comments_liked(comments_liked_json):
    """extract your_instagram_activity/likes/liked_comments -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in comments_liked_json["likes_comment_likes"]
    ]
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")




def extract_post_stories_and_comments_liked(zip_file_path):
    """Extract and combine liked posts, stories, and comments from ZIP file"""

    # Map file patterns to expected keys in the data structure
    key_mapping = {
        "liked_posts": "posts_liked",
        "story_likes": "stories_liked",
        "liked_comments": "comments_liked"
    }

    # Extract data from ZIP file
    combined_data = extract_multiple_files_from_zip(zip_file_path, patterns, key_mapping)

    if combined_data is None:
        return None

    # Initialize an empty DataFrame to store the combined results
    combined_df = pd.DataFrame(columns=["Datum", "Anzahl"])

    # Process each type of liked content
    data_sources = [
        ("posts_liked", extract_posts_liked),
        ("stories_liked", extract_stories_liked),
        ("comments_liked", extract_comments_liked)
    ]

    for source_key, extract_func in data_sources:
        source_data = combined_data.get(source_key, {})
        if source_data:
            source_df = extract_func(source_data)
            if not source_df.empty:
                if combined_df.empty:
                    combined_df = source_df.rename(columns={source_df.columns[1]: "Anzahl"})
                else:
                    source_df = source_df.rename(columns={source_df.columns[1]: f"Anzahl_{source_key}"})
                    combined_df = pd.merge(combined_df, source_df, on="Datum", how='outer')

    # Sum up all the like counts if we have multiple sources
    if not combined_df.empty and len(combined_df.columns) > 2:
        like_columns = [col for col in combined_df.columns if col != "Datum"]
        combined_df["Anzahl"] = combined_df[like_columns].sum(axis=1, skipna=True).fillna(0).astype(int)
        combined_df = combined_df[["Datum", "Anzahl"]]

    if not combined_df.empty:
        combined_df = combined_df.sort_values(by="Datum").reset_index(drop=True)

    return combined_df
