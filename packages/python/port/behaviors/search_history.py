import pandas as pd

from port.ddp import YoutubeDdp
from port.extraction_helpers import (
    activity_controls_with_header,
    format_timestamp,
    is_search_entry,
    sorted_by_timestamp,
    with_source,
)

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Suchverlauf",
}


def extract_search_history(source):
    """Search history: every search query with its timestamp."""

    entries, source_members = YoutubeDdp.of(source).select(is_search_entry)

    if not entries:
        return None

    search_data = [
        {
            "Timestamp": format_timestamp(entry.get("time", "")),
            # Kept as exported: the verb's place differs per language.
            "Search Query": entry.get("title", ""),
            "Activity Controls": activity_controls_with_header(entry),
        }
        for entry in entries
    ]

    return with_source(sorted_by_timestamp(pd.DataFrame(search_data)), source_members)
