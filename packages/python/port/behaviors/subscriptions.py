import pandas as pd

from port.extraction_helpers import find_csv_by_shape

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Abos",
}


def is_subscriptions_csv(df):
    """
    The subscriptions CSV always has 3 columns: Channel ID, Channel URL,
    Channel Title (in that order, regardless of locale). The channel URL
    itself isn't translated, so it reliably tells this file apart from
    similarly-shaped files like channel.csv (ID, Title, Visibility).
    """
    return df.iloc[:, 1].astype(str).str.contains("youtube.com/channel/").any()


def extract_subscriptions(file):
    """
    Extract YouTube subscriptions from ZIP file.
    Returns complete list of subscribed channels with Channel ID and Channel name.
    """

    subscriptions_csv = find_csv_by_shape(file, 3, is_subscriptions_csv)

    if subscriptions_csv is None:
        return None

    # Create output DataFrame with columns in correct order (by position,
    # since the column headers are localized)
    df = pd.DataFrame(
        {
            "Channel Name": subscriptions_csv.iloc[:, 2],
            "Channel ID": subscriptions_csv.iloc[:, 0],
        }
    )

    return df
