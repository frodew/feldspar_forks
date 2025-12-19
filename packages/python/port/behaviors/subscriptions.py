import zipfile
from io import StringIO

import pandas as pd

# Patterns to find the relevant files for this behavior (English and German)
patterns = ["subscriptions/subscriptions.csv", "Abos/Abos.csv"]

# Title used in prompt_consent() to describe this behavior
title = {
    "en": "Subscriptions",
}


def extract_subscriptions(zip_file_path):
    """
    Extract YouTube subscriptions from ZIP file.
    Returns complete list of subscribed channels with Channel ID and Channel name.
    """

    # Try to find the CSV file using either English or German pattern
    subscriptions_csv = None

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            file_names = zip_ref.namelist()

            # Find the subscriptions CSV file
            for pattern in patterns:
                for file_name in file_names:
                    if pattern in file_name and file_name.endswith(".csv"):
                        try:
                            with zip_ref.open(file_name) as csv_file:
                                csv_content = csv_file.read().decode("utf-8")
                                subscriptions_csv = pd.read_csv(StringIO(csv_content))
                                break
                        except Exception as e:
                            print(f"Error reading subscriptions CSV {file_name}: {e}")

                if subscriptions_csv is not None:
                    break

    except Exception as e:
        print(f"Error extracting subscriptions from ZIP: {e}")
        return None

    if subscriptions_csv is None or subscriptions_csv.empty:
        return None

    # Identify column names (check exact German column names from the file)
    channel_id_col = None
    channel_name_col = None

    # Check for exact column names first (German)
    if "Kanal-ID" in subscriptions_csv.columns:
        channel_id_col = "Kanal-ID"
    if "Kanaltitel" in subscriptions_csv.columns:
        channel_name_col = "Kanaltitel"

    # If not found, try English column names
    if channel_id_col is None:
        for col in subscriptions_csv.columns:
            if "Channel Id" in col or "Channel ID" in col:
                channel_id_col = col
                break

    if channel_name_col is None:
        for col in subscriptions_csv.columns:
            if "Channel Title" in col:
                channel_name_col = col
                break

    if channel_id_col is None or channel_name_col is None:
        return pd.DataFrame(columns=["Channel Name", "Channel ID"])

    # Create output DataFrame with columns in correct order
    df = pd.DataFrame(
        {
            "Channel Name": subscriptions_csv[channel_name_col],
            "Channel ID": subscriptions_csv[channel_id_col],
        }
    )

    return df
