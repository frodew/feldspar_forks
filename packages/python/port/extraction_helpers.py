import json
import re
import zipfile
from io import StringIO

import pandas as pd

CHANNEL_URL_RE = re.compile(r"^https://www\.youtube\.com/channel/[^/]+$")

# URL shapes that identify what an activity entry points at. They don't depend
# on the export language, unlike the file/folder names.
WATCH_URL_MARKER = "/watch?v="
SEARCH_URL_MARKER = "/results?search_query="
# Clicking an ad leaves YouTube for a Google-hosted click tracker, which is
# how a click is told apart from the impression. The path varies ("/url?",
# "/search?"), so match the host.
AD_CLICK_URL_PREFIX = "https://www.google.com/"


def in_youtube_folder(file_name):
    """Whether a ZIP member sits in a YouTube folder.

    "My Activity" exports put each product in its own folder, and YouTube's
    is exactly "YouTube" in every locale because it is a brand name - the
    folder *around* it is what gets translated ("My Activity", "Meine
    Aktivitäten", "Etkinliğim"). The older YouTube-product export instead
    uses "YouTube <and> YouTube Music", where only the conjunction is
    localized ("und", "ve", "i", "і", "e"), so match it on "YouTube Music".
    """
    folders = file_name.split("/")[:-1]
    return any(folder == "YouTube" or "YouTube Music" in folder for folder in folders)


def is_youtube_entry(entry):
    """Whether an activity entry belongs to the YouTube product.

    "products" is localized for most products ("Bildersuche", "Flüge"), but
    YouTube is a brand name and stays "YouTube" in every locale.
    """
    return isinstance(entry, dict) and "YouTube" in entry.get("products", [])


def is_channel_event(entry):
    """
    Whether an entry is a channel subscribe/unsubscribe event. These carry a
    bare channel URL (.../channel/CHANNEL_ID, no /watch?v= or
    /results?search_query=) and never have an activityControls value - a
    structural signature that holds regardless of locale.

    Subscribing and unsubscribing both land in this same set: telling them
    apart needs the (localized) verb in the entry's title, which isn't
    parsed here, so callers get an undifferentiated event log.
    """
    return (
        isinstance(entry, dict)
        and CHANNEL_URL_RE.match(entry.get("titleUrl", ""))
        and not entry.get("activityControls")
    )


def find_activity_entries(file, matches):
    """
    Find a Google activity JSON file inside the ZIP by structure rather than
    by file/folder name, since those names are localized (e.g. the watch
    history file is "watch-history.json" in English but
    "Wiedergabeverlauf.json" in German).

    The JSON keys themselves (title, titleUrl, time, ...) stay in English
    regardless of locale, so `matches(entry)` can identify the entries we
    want independent of language.

    Returns the file's YouTube entries, or None if no file has any match.

    Three guards matter for Takeout exports that bundle products beyond
    YouTube, where a first-match scan picks whichever product folder happens
    to sort first (e.g. "Bildersuche"). Only files in a YouTube folder are
    read at all, which also avoids parsing big unrelated files like Google
    Suche and Maps. Their entries are then filtered to the YouTube product.
    Finally the file with the *most* matches wins, which only ever arbitrates
    between the two history files of a YouTube-product export, since by then
    nothing outside YouTube remains.
    """
    best = None
    best_count = 0

    with zipfile.ZipFile(file, "r") as zip_ref:
        for file_name in zip_ref.namelist():
            if not file_name.endswith(".json") or not in_youtube_folder(file_name):
                continue
            try:
                with zip_ref.open(file_name) as json_file:
                    data = json.loads(json_file.read().decode("utf-8"))
            except Exception:
                continue

            if not isinstance(data, list):
                continue

            entries = [entry for entry in data if is_youtube_entry(entry)]
            count = sum(1 for entry in entries if matches(entry))
            if count > best_count:
                best = entries
                best_count = count

    return best


def title_url_contains(title_url_marker):
    """Build a `find_activity_entries` predicate matching a titleUrl substring."""
    return lambda entry: title_url_marker in entry.get("titleUrl", "")


def find_channel_event_entries(entries):
    """Filter activity entries down to channel subscribe/unsubscribe events."""
    return [entry for entry in entries if is_channel_event(entry)]


def activity_controls_with_header(entry):
    """Join an entry's activity controls into one string, led by its header.

    "header" is the sub-product ("YouTube", "YouTube Music"). It rides in this
    column rather than one of its own: that repeats "YouTube" on most rows,
    but keeps the sub-product in the donation instead of discarding it.

    Entries with no activityControls sometimes carry a "description" with a
    retention countdown (e.g. "Ablaufdatum: 02.11.2026") - use that instead,
    rather than adding a column that is empty for nearly every other row.
    """
    controls = entry.get("activityControls", [])
    controls_str = ", ".join(controls) if controls else entry.get("description", "")
    header = entry.get("header", "")
    return ", ".join(part for part in (header, controls_str) if part)


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
