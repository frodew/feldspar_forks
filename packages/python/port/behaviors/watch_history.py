from datetime import datetime

import pandas as pd

from port.extraction_helpers import (
    AD_CLICK_URL_PREFIX,
    SEARCH_URL_MARKER,
    WATCH_URL_MARKER,
    activity_controls_with_header,
    find_activity_entries,
    is_channel_event,
    title_url_contains,
    with_source,
)

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wiedergabeverlauf",
}


def format_timestamp(timestamp_str):
    """Convert ISO timestamp to readable format: YYYY-MM-DD HH:MM:SS.mmm"""
    try:
        if not timestamp_str:
            return ""
        # Parse ISO format and convert to readable format
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[
            :-3
        ]  # Remove last 3 digits of microseconds
    except:
        return timestamp_str


def activity_id_and_kind(title_url):
    """Identify what an entry points at, from the URL shape alone.

    Returns (id, kind). `kind` is empty for an ordinary video view, which is
    the overwhelming majority, so the Details column stays empty for those.
    """
    if not title_url:
        return "", ""
    if WATCH_URL_MARKER in title_url:
        return title_url.split("watch?v=")[-1].split("&")[0], ""
    if title_url.startswith(AD_CLICK_URL_PREFIX):
        # The whole destination is already in the entry's title, so there is
        # no id worth pulling out separately.
        return "", "clicked ad"
    if "/post/" in title_url:
        return title_url.split("/post/")[-1].split("?")[0], "community post"
    if "/playlist" in title_url:
        return title_url.split("list=")[-1].split("&")[0], "playlist"
    if "/shorts/" in title_url:
        return title_url.split("/shorts/")[-1].split("?")[0], "shorts"
    return "", "other"


def extract_watch_history(file):
    """
    Extract YouTube watch history from ZIP file.

    Keeps every YouTube activity entry except searches and subscribe events,
    which have their own tables. So alongside video views this carries ad
    clicks, community posts, playlist saves and shared Shorts, each labelled
    in the Details column rather than split off into a table of its own.
    Sorted by time with newest on top.
    """

    # Find the watch history file by structure, regardless of its (localized)
    # file/folder name
    entries, source = find_activity_entries(file, title_url_contains(WATCH_URL_MARKER))

    if entries is None:
        return None

    # Extract data from each entry
    video_data = []

    for entry in entries:
        title_url = entry.get("titleUrl", "")

        # Searches and subscribe/unsubscribe events get their own tables.
        if SEARCH_URL_MARKER in title_url or is_channel_event(entry):
            continue

        # Entries with no titleUrl at all are watch-shaped placeholders
        # Google didn't attach a video to: either a redacted "hidden
        # section" or a since-deleted video. They carry no video/channel
        # info to extract, but are kept here (instead of dropped) so the
        # data isn't silently lost - they can be filtered back out later.

        video_id, kind = activity_id_and_kind(title_url)

        # Extract channel information from subtitles if available
        channel_id = None
        channel_name = None

        if "subtitles" in entry and len(entry["subtitles"]) > 0:
            subtitle = entry["subtitles"][0]
            if "url" in subtitle:
                channel_url = subtitle["url"]
                # Extract channel ID from URL (format: http://www.youtube.com/channel/CHANNEL_ID)
                if "/channel/" in channel_url:
                    channel_id = channel_url.split("/channel/")[-1]
            if "name" in subtitle:
                channel_name = subtitle["name"]

        # Extract timestamp
        timestamp = entry.get("time", "")

        activity_controls_str = activity_controls_with_header(entry)

        # Video title is kept as exported (e.g. "Watched X" or "X angesehen"):
        # the verb is placed differently in every language, so there's no
        # reliable way to strip it without hardcoding each language's grammar
        video_title = entry.get("title", "")

        # Ads carry a "details" entry naming Google Ads as the source, kept
        # here verbatim. It marks impressions and clicks alike, so the kind
        # from the URL shape is appended to tell those apart. The retention
        # countdown (e.g. "Ablaufdatum: 02.11.2026") rides along as well, but
        # only for entries that named no activity control: those are the ones
        # that used to carry it in the Activity Controls column, and keeping
        # that column free of it is what makes "no control named" detectable.
        details = entry.get("details", [])
        countdown = "" if entry.get("activityControls") else entry.get("description", "")
        details_str = ", ".join(
            part
            for part in [d.get("name", "") for d in details] + [kind, countdown]
            if part
        )

        video_data.append(
            {
                "Timestamp": format_timestamp(timestamp),
                "Video Title": video_title,
                "Video ID": video_id if video_id else "",
                "Channel Name": channel_name if channel_name else "",
                "Channel ID": channel_id if channel_id else "",
                "Activity Controls": activity_controls_str,
                "Details": details_str,
            }
        )

    if not video_data:
        return with_source(
            pd.DataFrame(
                columns=[
                    "Timestamp",
                    "Video Title",
                    "Video ID",
                    "Channel Name",
                    "Channel ID",
                    "Activity Controls",
                    "Details",
                ]
            ),
            source,
        )

    # Create DataFrame
    df = pd.DataFrame(video_data)

    # Sort by timestamp (newest on top)
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["Timestamp_sort"])

    return with_source(df, source)
