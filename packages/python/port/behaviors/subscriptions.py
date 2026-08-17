from datetime import datetime

import pandas as pd

from port.extraction_helpers import (
    find_activity_entries,
    find_channel_event_entries,
    find_csv_by_shape,
)

# Marks a "My Activity" entry as a watch (rather than a search): used here
# only to locate the right JSON file, the same way watch_history.py does.
WATCH_URL_MARKER = "/watch?v="

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Abos",
}


def format_timestamp(timestamp_str):
    """Convert ISO timestamp to readable format: YYYY-MM-DD HH:MM:SS.mmm"""
    try:
        if not timestamp_str:
            return ""
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except:
        return timestamp_str


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

    Prefers subscriptions.csv (the current, point-in-time list of
    subscribed channels). Google "My Activity" exports don't include that
    CSV at all, so as a fallback this reconstructs a subscribe/unsubscribe
    event log from the activity JSON instead - timestamped, but not a
    current-state list, and not split into subscribe vs. unsubscribe since
    that direction is only written in a (localized) verb we don't parse.
    """

    subscriptions_csv = find_csv_by_shape(file, 3, is_subscriptions_csv)

    if subscriptions_csv is not None:
        # Columns in correct order (by position, since the column headers
        # are localized)
        return pd.DataFrame(
            {
                "Channel Name": subscriptions_csv.iloc[:, 2],
                "Channel ID": subscriptions_csv.iloc[:, 0],
            }
        )

    entries = find_activity_entries(file, WATCH_URL_MARKER)
    if entries is None:
        return None

    channel_events = find_channel_event_entries(entries)

    event_data = []
    for entry in channel_events:
        title_url = entry.get("titleUrl", "")
        channel_id = title_url.split("/channel/")[-1]

        event_data.append(
            {
                "Timestamp": format_timestamp(entry.get("time", "")),
                # Kept as exported (e.g. "X subscribed" or "X abonniert"):
                # the verb - and whether it means subscribed or
                # unsubscribed - is locale-dependent, so it isn't stripped
                # or classified here.
                "Event": entry.get("title", ""),
                "Channel ID": channel_id,
            }
        )

    if not event_data:
        return pd.DataFrame(columns=["Timestamp", "Event", "Channel ID"])

    df = pd.DataFrame(event_data)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return df
