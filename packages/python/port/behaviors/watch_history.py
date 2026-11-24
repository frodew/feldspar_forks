import pandas as pd

from port.ddp import YoutubeDdp
from port.extraction_helpers import (
    AD_CLICK_URL_PREFIX,
    WATCH_URL_MARKER,
    activity_controls_with_header,
    format_timestamp,
    is_watch_entry,
    sorted_by_timestamp,
    with_source,
)

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wiedergabeverlauf",
}


def activity_id_and_kind(title_url):
    """What an entry points at, from the URL shape alone, as (id, kind).

    `kind` is empty for an ordinary video view, the overwhelming majority, so
    the Details column stays empty for those.
    """
    if not title_url:
        return "", ""
    if WATCH_URL_MARKER in title_url:
        return title_url.split("watch?v=")[-1].split("&")[0], ""
    if title_url.startswith(AD_CLICK_URL_PREFIX):
        # The whole destination is in the entry's title already.
        return "", "clicked ad"
    if "/post/" in title_url:
        return title_url.split("/post/")[-1].split("?")[0], "community post"
    if "/playlist" in title_url:
        return title_url.split("list=")[-1].split("&")[0], "playlist"
    if "/shorts/" in title_url:
        return title_url.split("/shorts/")[-1].split("?")[0], "shorts"
    return "", "other"


def channel_of(entry):
    """The channel an entry names, as (name, id); either may be empty."""
    subtitle = (entry.get("subtitles") or [{}])[0]
    channel_url = subtitle.get("url", "")
    channel_id = channel_url.split("/channel/")[-1] if "/channel/" in channel_url else ""
    return subtitle.get("name", ""), channel_id


def details_of(entry, kind):
    """The Details cell: what Google said about the entry, plus its kind.

    Google's marker ("Von Google Anzeigen") only appears for donors who enabled
    personalized ads; everyone else's ads are here too, just unmarked. The
    retention countdown rides along only for entries that named no activity
    control, which keeps that column free to mark "no control named".
    """
    names = [detail.get("name", "") for detail in entry.get("details", [])]
    countdown = "" if entry.get("activityControls") else entry.get("description", "")
    return ", ".join(part for part in names + [kind, countdown] if part)


def extract_watch_history(source):
    """Watch history: every YouTube entry except searches and channel events.

    So alongside video views this carries ad impressions and clicks, community
    posts, playlist saves and shared Shorts, each labelled in Details rather
    than split into a table of its own.
    """

    entries, source_members = YoutubeDdp.of(source).select(is_watch_entry)

    if not entries:
        return None

    video_data = []

    for entry in entries:
        # No titleUrl: a hidden section, a deleted video, an ad impression.
        video_id, kind = activity_id_and_kind(entry.get("titleUrl", ""))
        channel_name, channel_id = channel_of(entry)

        video_data.append(
            {
                "Timestamp": format_timestamp(entry.get("time", "")),
                # Kept as exported: the verb's place differs per language.
                "Video Title": entry.get("title", ""),
                "Video ID": video_id,
                "Channel Name": channel_name,
                "Channel ID": channel_id,
                "Activity Controls": activity_controls_with_header(entry),
                "Details": details_of(entry, kind),
            }
        )

    return with_source(sorted_by_timestamp(pd.DataFrame(video_data)), source_members)
