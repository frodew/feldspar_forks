import pandas as pd

from port.ddp import YoutubeDdp
from port.extraction_helpers import format_timestamp, sorted_by_timestamp, with_source

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Kommentare",
}


def extract_comments(source):
    """Comments, which only a YouTube-DDP carries; a MyActivity-DDP has none."""

    ddp = YoutubeDdp.of(source)

    if ddp.comments_csv is None:
        return None

    # Columns by position, since the headers are localized
    df = pd.DataFrame(
        {
            "Timestamp": ddp.comments_csv.iloc[:, 2].apply(format_timestamp),
            "Video ID": ddp.comments_csv.iloc[:, 4],
        }
    )

    return with_source(sorted_by_timestamp(df), ddp.comments_csv_source)
