import pandas as pd

from port.ddp import YoutubeDdp
from port.extraction_helpers import (
    format_timestamp,
    is_channel_event,
    sorted_by_timestamp,
    with_source,
)

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Abos",
}


def extract_subscriptions(source):
    """Subscriptions, preferring the subscribe/unsubscribe event log.

    The event log is timestamped where subscriptions.csv is only a snapshot of
    the channels currently followed; the CSV is the fallback, since a
    MyActivity-DDP has no CSV and a YouTube-DDP has no events. Subscribe and
    unsubscribe are not split: the direction is only in the localized verb.
    """

    ddp = YoutubeDdp.of(source)
    channel_events, source_members = ddp.select(is_channel_event)

    if channel_events:
        event_data = [
            {
                "Timestamp": format_timestamp(entry.get("time", "")),
                # Kept as exported ("X subscribed", "X abonniert").
                "Event": entry.get("title", ""),
                "Channel ID": entry.get("titleUrl", "").split("/channel/")[-1],
            }
            for entry in channel_events
        ]
        return with_source(sorted_by_timestamp(pd.DataFrame(event_data)), source_members)

    if ddp.subscriptions_csv is not None:
        # Columns by position, since the headers are localized
        return with_source(
            pd.DataFrame(
                {
                    "Channel Name": ddp.subscriptions_csv.iloc[:, 2],
                    "Channel ID": ddp.subscriptions_csv.iloc[:, 0],
                }
            ),
            ddp.subscriptions_csv_source,
        )

    return None
