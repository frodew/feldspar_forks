from port.extraction_helpers import epoch_to_date, extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["ads_clicked"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Werbung angeklickt? [pro Tag]",
}

def extract_ads_clicked(zip_file_path):
    """Extract ads clicked data from ZIP file -> list of product names per day"""

    # Extract data from ZIP file
    ads_clicked_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if ads_clicked_json is None:
        return None

    timestamps = [
        t["string_list_data"][0]["timestamp"]
        for t in ads_clicked_json["impressions_history_ads_clicked"]
    ]  # get list with timestamps in epoch format
    dates = [epoch_to_date(t) for t in timestamps]  # convert epochs to dates
    products = [i["title"] for i in ads_clicked_json["impressions_history_ads_clicked"]]

    adds_clicked_df = pd.DataFrame({"Datum": dates, "Angeklickte Werbung": products})

    aggregated_df = adds_clicked_df.groupby("Datum")["Angeklickte Werbung"].agg(list).reset_index()

    return aggregated_df
