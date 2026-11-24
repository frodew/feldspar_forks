import re
from datetime import datetime
from io import StringIO

import pandas as pd

CHANNEL_URL_RE = re.compile(r"^https://www\.youtube\.com/channel/[^/]+$")

# URL shapes identifying what an entry points at, independent of the export language.
WATCH_URL_MARKER = "/watch?v="
SEARCH_URL_MARKER = "/results?search_query="
# A clicked ad leaves for a Google click tracker, whose path varies - match the host.
AD_CLICK_URL_PREFIX = "https://www.google.com/"


def in_youtube_folder(file_name):
    """Whether a ZIP member sits in a YouTube folder.

    A MyActivity-DDP puts each product in its own folder, and YouTube's is
    exactly "YouTube" in every locale because it is a brand name; the folder
    around it is the translated one ("Meine Aktivitäten", "Etkinliğim"). A
    YouTube-DDP uses "YouTube <and> YouTube Music", where only the conjunction
    is localized ("und", "ve", "i", "і", "e"), so match on "YouTube Music".
    """
    folders = file_name.split("/")[:-1]
    return any(folder == "YouTube" or "YouTube Music" in folder for folder in folders)


def is_youtube_entry(entry):
    """Whether an entry belongs to the YouTube product.

    "products" is localized for most products ("Bildersuche", "Flüge"), but
    YouTube is a brand name and stays "YouTube" in every locale.
    """
    return isinstance(entry, dict) and "YouTube" in entry.get("products", [])


def is_search_entry(entry):
    """Whether an entry is a search, by URL shape rather than localized text."""
    return SEARCH_URL_MARKER in entry.get("titleUrl", "")


def is_channel_event(entry):
    """Whether an entry is a channel subscribe/unsubscribe event.

    These carry a bare channel URL and never an activityControls value, a
    signature that holds in every locale. Subscribing and unsubscribing both
    land here: the direction is only in the localized verb, which isn't parsed.
    """
    return bool(
        CHANNEL_URL_RE.match(entry.get("titleUrl", ""))
        and not entry.get("activityControls")
    )


def is_watch_entry(entry):
    """Whether an entry belongs in the watch table: anything but the other two.

    Searches and channel events have tables of their own; everything else stays
    here, including ad impressions that carry no titleUrl at all.
    """
    return not is_search_entry(entry) and not is_channel_event(entry)


def activity_controls_with_header(entry):
    """An entry's activity controls as one string, led by its header.

    "header" is the sub-product ("YouTube", "YouTube Music"), carried here
    rather than in a column of its own. Nothing else goes in: the value is the
    header alone exactly when the entry named no activity control, which is
    what lets the analysis tell that apart without matching localized text.
    """
    controls = entry.get("activityControls", [])
    header = entry.get("header", "")
    return ", ".join(part for part in (header, ", ".join(controls)) if part)


def format_timestamp(timestamp_str):
    """An ISO timestamp as YYYY-MM-DD HH:MM:SS.mmm, or unchanged if unreadable."""
    try:
        if not timestamp_str:
            return ""
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except:
        return timestamp_str


def sorted_by_timestamp(df):
    """The table newest first, with unreadable timestamps last."""
    df["Timestamp_sort"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.sort_values(by="Timestamp_sort", ascending=False).reset_index(drop=True)
    return df.drop(columns=["Timestamp_sort"])


def find_csv_by_shape(zip_ref, members, num_columns, matches):
    """A CSV found by its shape, since its file name is localized.

    Names and column headers are translated (subscriptions.csv becomes Abos.csv
    with headers "Kanal-ID, Kanal-URL, Kanaltitel"), while column order and cell
    values are not, so `matches` confirms a candidate by content and callers
    read it by position. Returns the table and its member, or (None, "").
    """
    for file_name in members:
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
            return df, file_name

    return None, ""


def with_source(df, source):
    """Tag a table with the ZIP member(s) it came from.

    Rides in `DataFrame.attrs` so it reaches the donation metadata without
    becoming a column that repeats on every row participants see.
    """
    df.attrs["source"] = source
    return df
