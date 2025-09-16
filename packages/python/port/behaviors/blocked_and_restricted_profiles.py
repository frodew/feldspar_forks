from port.extraction_helpers import epoch_to_date, extract_multiple_files_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["blocked_profiles", "restricted_profiles"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie andere Profile blockiert und eingeschränkt? [pro Tag]",
}

def extract_blocked_profiles(blocked_profiles_json):
    """extract connections/followers_and_following/blocked_profiles -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in blocked_profiles_json["relationships_blocked_users"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_restricted_profiles(restricted_profiles_json):
    """extract connections/followers_and_following/restricted_accounts -> count per day"""

    dates = [
        epoch_to_date(t["string_list_data"][0]["timestamp"])
        for t in restricted_profiles_json["relationships_restricted_users"]
    ]  # get list with timestamps in epoch format
    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")


def extract_blocked_and_restricted_profiles(zip_file_path):
    """Extract and combine blocked profiles and restricted profiles from ZIP file"""

    # Extract data from ZIP file
    combined_data = extract_multiple_files_from_zip(zip_file_path, patterns)

    if combined_data is None:
        return None

    # Initialize an empty DataFrame to store the combined results
    combined_df = pd.DataFrame(columns=["Datum", "Anzahl"])

    # Extract blocked profiles if available
    blocked_data = combined_data.get("blocked_profiles", {})
    if blocked_data:
        blocked_df = extract_blocked_profiles(blocked_data)
        if not blocked_df.empty:
            combined_df = blocked_df.rename(columns={blocked_df.columns[1]: "Anzahl"})

    # Extract restricted profiles if available
    restricted_data = combined_data.get("restricted_profiles", {})
    if restricted_data:
        restricted_df = extract_restricted_profiles(restricted_data)
        if not restricted_df.empty:
            if not combined_df.empty:
                restricted_df = restricted_df.rename(columns={restricted_df.columns[1]: "Anzahl"})
                combined_df = pd.merge(combined_df, restricted_df, on="Datum", how='outer', suffixes=('_blocked', '_restricted'))
                combined_df["Anzahl"] = combined_df.filter(like="Anzahl").sum(axis=1, skipna=True).fillna(0).astype(int)
                combined_df = combined_df[["Datum", "Anzahl"]]
            else:
                combined_df = restricted_df.rename(columns={restricted_df.columns[1]: "Anzahl"})

    if not combined_df.empty:
        combined_df = combined_df.sort_values(by="Datum").reset_index(drop=True)

    return combined_df
