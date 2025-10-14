from port.extraction_helpers import epoch_to_date, extract_multiple_files_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["countdowns", "emoji_sliders", "polls", "questions", "quizzes"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie mit Stories interagiert? [pro Tag]",
}


def extract_story_interaction_countdowns(story_interaction_countdowns_json):
    """extract your_instagram_activity/story_sticker_interactions/countdowns -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in story_interaction_countdowns_json["story_activities_countdowns"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_story_interaction_emoji_sliders(story_interaction_emoji_sliders_json):
    """extract your_instagram_activity/story_sticker_interactions/emoji_sliders -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in story_interaction_emoji_sliders_json["story_activities_emoji_sliders"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_story_interaction_polls(story_interaction_polls_json):
    """extract your_instagram_activity/story_sticker_interactions/polls -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in story_interaction_polls_json["story_activities_polls"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_story_interaction_questions(story_interaction_questions_json):
    """extract your_instagram_activity/story_sticker_interactions/questions -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in story_interaction_questions_json["story_activities_questions"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_story_interaction_quizzes(story_interaction_quizzes_json):
    """extract your_instagram_activity/story_sticker_interactions/quizzes -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in story_interaction_quizzes_json["story_activities_quizzes"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_story_interactions(zip_file_path):
    """Extract and combine all story interactions from ZIP file"""

    # Extract data from ZIP file
    combined_data = extract_multiple_files_from_zip(zip_file_path, patterns)

    if combined_data is None:
        return None

    # Initialize an empty DataFrame to store the combined results
    combined_df = pd.DataFrame(columns=["Datum", "Anzahl"])

    # List of all story interaction types and their extraction functions
    interaction_types = [
        ("countdowns", extract_story_interaction_countdowns),
        ("emoji_sliders", extract_story_interaction_emoji_sliders),
        ("polls", extract_story_interaction_polls),
        ("questions", extract_story_interaction_questions),
        ("quizzes", extract_story_interaction_quizzes),
    ]

    # Process each type of story interaction
    for interaction_type, extract_func in interaction_types:
        data = combined_data.get(interaction_type, {})
        if data:
            df = extract_func(data)
            if not df.empty:
                if combined_df.empty:
                    combined_df = df.rename(columns={df.columns[1]: "Anzahl"})
                else:
                    df = df.rename(
                        columns={df.columns[1]: f"Anzahl_{interaction_type}"}
                    )
                    combined_df = pd.merge(combined_df, df, on="Datum", how="outer")

    # Sum up all interaction counts if we have multiple sources
    if not combined_df.empty and len(combined_df.columns) > 2:
        interaction_columns = [col for col in combined_df.columns if col != "Datum"]
        combined_df["Anzahl"] = (
            combined_df[interaction_columns]
            .sum(axis=1, skipna=True)
            .fillna(0)
            .astype(int)
        )
        combined_df = combined_df[["Datum", "Anzahl"]]

    if not combined_df.empty:
        combined_df = combined_df.sort_values(by="Datum").reset_index(drop=True)

    return combined_df
