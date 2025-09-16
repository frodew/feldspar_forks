from port.extraction_helpers import epoch_to_date, extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["media/reels.json"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Reels veröffentlicht? [pro Tag]",
}

def extract_reels_created(zip_file_path):
    """Extract reels created data from ZIP file -> count per day"""

    # Extract data from ZIP file
    reels_created_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if reels_created_json is None:
        return None

    dates = []

    for reel in reels_created_json.get("ig_reels_media", []):
        # Get the first media item in the list (typically there's only one)
        media_items = reel.get("media", [])
        if not media_items:
            continue

        media_item = media_items[0]  # Access the first element of the list
        date = epoch_to_date(media_item.get("creation_timestamp", ""))
        dates.append(date)

    dates_df = pd.DataFrame(dates, columns=["Datum"])  # convert to df

    aggregated_df = dates_df.groupby(["Datum"])[
        "Datum"
    ].size()  # count number of rows per day

    return aggregated_df.reset_index(name="Anzahl")
