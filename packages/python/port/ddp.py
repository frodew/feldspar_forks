"""Everything the donation needs out of one Takeout ZIP, read in a single pass.

Both DDP types land here, in JSON or in HTML: the YouTube-DDP ("YouTube and
YouTube Music", history plus CSVs) and the MyActivity-DDP (one file per
product). Nothing is located by file name, since those are localized in both -
only brand-name folders, the English JSON keys, URL shapes and CSV column
shapes are relied on.
"""

import json
import logging
import zipfile

from port.extraction_helpers import (
    find_csv_by_shape,
    in_youtube_folder,
    is_youtube_entry,
)
from port.html_activity import parse_activity_html

logger = logging.getLogger(__name__)


def is_subscriptions_csv(df):
    """Whether a 3-column CSV is the subscriptions one: ID, URL, Title.

    The URL isn't translated, which tells this file apart from similarly
    shaped ones like channel.csv (ID, Title, Visibility).
    """
    return df.iloc[:, 1].astype(str).str.contains("youtube.com/channel/").any()


def is_comments_csv(df):
    """Whether a 6-column CSV is the comments one: ID, Channel, Time, Price, Video, Text.

    The text is a JSON blob ({"text": "..."}), which tells this file apart
    from other 6-column ones.
    """
    return df.iloc[:, 5].astype(str).str.contains('{"text"', regex=False).any()


def parse_activity_json(source):
    data = json.loads(source)
    return data if isinstance(data, list) else []


def read_members(zip_ref, members, suffix, parse):
    """Every member with `suffix` parsed, each entry paired with its member."""
    entries = []
    for file_name in members:
        if not file_name.endswith(suffix):
            continue
        try:
            with zip_ref.open(file_name) as member:
                data = parse(member.read().decode("utf-8"))
        except Exception:
            logger.exception(f"could not read {file_name}")
            continue
        entries.extend((entry, file_name) for entry in data if is_youtube_entry(entry))
    return entries


def read_activity_entries(zip_ref, members):
    """The activity entries of every YouTube-folder member, pooled.

    Pooling is what makes file names irrelevant: a YouTube-DDP splits history
    across two files and a MyActivity-DDP keeps one, and either way a table is
    just a row filter over the pool. JSON wins over HTML so that a DDP holding
    both formats doesn't count every row twice.
    """
    entries = read_members(zip_ref, members, ".json", parse_activity_json)
    if entries:
        return entries
    return read_members(zip_ref, members, ".html", parse_activity_html)


class YoutubeDdp:
    """A participant's uploaded ZIP, parsed once and queried by the behaviors."""

    def __init__(self, file):
        self.verdict = "valid"
        self.entries = []
        self.subscriptions_csv, self.subscriptions_csv_source = None, ""
        self.comments_csv, self.comments_csv_source = None, ""

        try:
            self._read(file)
        except zipfile.BadZipFile:
            logger.warning("invalid ZIP file")
            self.verdict = "invalid_file_zip"
            return
        except Exception as error:
            logger.exception(f"could not read the ZIP file: {error}")
            self.verdict = "invalid_file_error"
            return

        if not self.entries and not self.has_csv:
            self.verdict = "invalid_no_ddp"

    def _read(self, file):
        with zipfile.ZipFile(file, "r") as zip_ref:
            # Only YouTube folders are read, so other products contribute nothing.
            members = [name for name in zip_ref.namelist() if in_youtube_folder(name)]
            self.entries = read_activity_entries(zip_ref, members)
            self.subscriptions_csv, self.subscriptions_csv_source = find_csv_by_shape(
                zip_ref, members, 3, is_subscriptions_csv
            )
            self.comments_csv, self.comments_csv_source = find_csv_by_shape(
                zip_ref, members, 6, is_comments_csv
            )

    @classmethod
    def of(cls, source):
        """Accept either an uploaded ZIP or an already-parsed DDP."""
        return source if isinstance(source, cls) else cls(source)

    @property
    def has_csv(self):
        return self.subscriptions_csv is not None or self.comments_csv is not None

    @property
    def sources(self):
        """The members the pooled entries came from, for logging."""
        return ", ".join(sorted({member for _, member in self.entries}))

    def select(self, matches):
        """The entries matching `matches`, and the members they came from."""
        selected = [pair for pair in self.entries if matches(pair[0])]
        sources = ", ".join(sorted({member for _, member in selected}))
        return [entry for entry, _ in selected], sources
