from port.extraction_helpers import epoch_to_date, extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["followers_1"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie neue Follower? [pro Tag]",
}


def extract_followers_new(zip_file_path):
    """Extract new followers data from ZIP file -> count per day"""

    # Extract data from ZIP file
    followers_new_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if followers_new_json is None:
        return None

    # file can just be dict and not list if only one follower
    if isinstance(followers_new_json, dict):
        dates = [epoch_to_date(followers_new_json["string_list_data"][0]["timestamp"])]
    else:
        dates = [
            epoch_to_date(t["string_list_data"][0]["timestamp"])
            for t in followers_new_json
        ]

    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")
