import json
import re
import zipfile
from io import StringIO

import pandas as pd

CHANNEL_URL_RE = re.compile(r"^https://www\.youtube\.com/channel/[^/]+$")


def find_activity_entries(file, title_url_marker):
    """
    Find a Google "My Activity" JSON file inside the ZIP by structure rather
    than by file/folder name, since those names are localized (e.g. the
    watch history file is "watch-history.json" in English but
    "Wiedergabeverlauf.json" in German).

    The JSON keys themselves (title, titleUrl, time, ...) stay in English
    regardless of locale, and the "titleUrl" shape reliably tells watch
    entries (.../watch?v=...) apart from search entries
    (.../results?search_query=...) independent of language. So we look for
    the JSON file that has entries whose titleUrl contains `title_url_marker`.

    Returns the parsed list of entries, or None if no matching file exists.
    """
    with zipfile.ZipFile(file, "r") as zip_ref:
        for file_name in zip_ref.namelist():
            if not file_name.endswith(".json"):
                continue
            try:
                with zip_ref.open(file_name) as json_file:
                    data = json.loads(json_file.read().decode("utf-8"))
            except Exception:
                continue

            if not isinstance(data, list):
                continue

            if any(
                isinstance(entry, dict) and title_url_marker in entry.get("titleUrl", "")
                for entry in data
            ):
                return data

    return None


def find_channel_event_entries(entries):
    """
    Filter "My Activity" entries down to channel subscribe/unsubscribe
    events. These carry a bare channel URL (.../channel/CHANNEL_ID, no
    /watch?v= or /results?search_query=) and never have an activityControls
    value - a structural signature that holds regardless of locale.

    Subscribing and unsubscribing both land in this same set: telling them
    apart needs the (localized) verb in the entry's title, which isn't
    parsed here, so callers get an undifferentiated event log.
    """
    return [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and CHANNEL_URL_RE.match(entry.get("titleUrl", ""))
        and not entry.get("activityControls")
    ]


def find_csv_by_shape(file, num_columns, matches):
    """
    Find a CSV file inside the ZIP by its shape rather than by file/folder
    name, since those names (and the column headers) are localized (e.g.
    subscriptions.csv becomes Abos.csv with headers "Kanal-ID, Kanal-URL,
    Kanaltitel" in German). Column order stays the same across locales, so
    callers should read the returned DataFrame by column position.

    `matches` is called with the parsed DataFrame and should return True if
    it looks like the file we want (e.g. by checking cell values, which are
    not translated).

    Returns the parsed DataFrame, or None if no matching file exists.
    """
    with zipfile.ZipFile(file, "r") as zip_ref:
        for file_name in zip_ref.namelist():
            if not file_name.endswith(".csv"):
                continue
            try:
                with zip_ref.open(file_name) as csv_file:
                    df = pd.read_csv(StringIO(csv_file.read().decode("utf-8")))
            except Exception:
                continue

            if df.empty or len(df.columns) != num_columns:
                continue

            if matches(df):
                return df

    return None
