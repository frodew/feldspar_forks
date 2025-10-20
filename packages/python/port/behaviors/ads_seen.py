from port.extraction_helpers import epoch_to_date, extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["ads_and_topics/ads_viewed"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Werbung gesehen? [pro Tag]",
}


def extract_ads_seen(zip_file_path):
    """Extract ads seen data from ZIP file -> list of authors per day"""

    # Extract data from ZIP file
    ads_seen_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if ads_seen_json is None:
        return None

    timestamps = [
        t["string_map_data"]["Time"]["timestamp"]
        for t in ads_seen_json["impressions_history_ads_seen"]
    ]  # get list with timestamps in epoch format (if author exists)
    dates = [epoch_to_date(t) for t in timestamps]  # convert epochs to dates
    authors = [
        i["string_map_data"]["Author"]["value"]
        if "Author" in i["string_map_data"]
        else "Unbekanntes Konto"
        for i in ads_seen_json["impressions_history_ads_seen"]
    ]  # not for all viewed ads there is an author!

    adds_viewed_df = pd.DataFrame({"Datum": dates, "Gesehene Konten": authors})

    aggregated_df = (
        adds_viewed_df.groupby("Datum")["Gesehene Konten"].agg(list).reset_index()
    )

    return aggregated_df
