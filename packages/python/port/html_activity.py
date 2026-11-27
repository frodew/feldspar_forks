"""Read an activity HTML export into the same entry dicts the JSON export carries."""

import html
import io
import re
from datetime import datetime, timedelta

# Cards are read one at a time off a chunked stream: a 137 MB export holding a
# single emoji is a 4-bytes-per-character string, far too big to hold whole.
CELL_START = '<div class="outer-cell'
CHUNK_SIZE = 1 << 20
HEADER_RE = re.compile(r'<p class="mdl-typography--title">(.*?)<br>', re.S)
BODY_RE = re.compile(
    r'<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">(.*?)</div>',
    re.S,
)
CAPTION_RE = re.compile(r'mdl-typography--caption">(.*?)</div>', re.S)
LINK_RE = re.compile(r'<a href="([^"]*)"[^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
SECTION_RE = re.compile(r"<b>(.*?)</b>", re.S)

TIME_RE = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})\s*(AM|PM)?", re.I)
DATE_NUMERIC_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
DATE_MONTH_FIRST_RE = re.compile(r"(\w+)\.?\s+(\d{1,2}),?\s+(\d{4})")
DATE_DAY_FIRST_RE = re.compile(r"(\d{1,2})\.?\s+(\w+)\.?,?\s+(\d{4})")

# A file renders every timestamp in one offset, so a flat table is exact.
UTC_OFFSETS = {"UTC": 0, "GMT": 0, "MEZ": 1, "CET": 1, "WAT": 1, "MESZ": 2, "CEST": 2}

# Abbreviated month names per locale; no abbreviation means two months.
MONTHS = {}
for _language in [
    "jan feb mar apr may jun jul aug sep oct nov dec",  # en
    "oca şub mar nis may haz tem ağu eyl eki kas ara",  # tr
    "gen feb mar apr mag giu lug ago set ott nov dic",  # it
    "sty lut mar kwi maj cze lip sie wrz paź lis gru",  # pl
    "січ лют бер кві трав черв лип серп вер жовт лист груд",  # uk
]:
    MONTHS.update({name: number for number, name in enumerate(_language.split(), start=1)})


def strip_tags(fragment):
    """Tags and the indent entity Google pads caption lines with, dropped."""
    return TAG_RE.sub("", fragment).replace("&emsp;", "")


def is_blank(fragment):
    return not strip_tags(fragment).strip()


def unescape(fragment):
    """A fragment's text, with no-break spaces made plain and nothing trimmed.

    Google writes the verb separator as &nbsp; where the JSON uses a space.
    Trailing spaces are content: a query searched as "trump biden " keeps it.
    """
    return html.unescape(strip_tags(fragment)).replace("\xa0", " ")


def to_iso_utc(rendered):
    """A rendered local timestamp as the ISO UTC string the JSON uses.

    Returned unchanged when the date format or the timezone is one we cannot
    read, so an unknown locale costs the UTC instant but never a row.
    """
    clock = TIME_RE.search(rendered)
    if not clock:
        return rendered

    date_part = rendered[: clock.start()]
    numeric = DATE_NUMERIC_RE.search(date_part)
    if numeric:
        day, month, year = (int(part) for part in numeric.groups())
    else:
        named = DATE_MONTH_FIRST_RE.search(date_part) or DATE_DAY_FIRST_RE.search(date_part)
        if not named:
            return rendered
        name, day, year = named.groups()
        if name.isdigit():  # day-first order, so the groups come back swapped
            day, name = name, day
        month = MONTHS.get(name.lower().rstrip("."))
        if month is None:
            return rendered
        day, year = int(day), int(year)

    hour, minute, second, meridiem = clock.groups()
    hour = int(hour)
    if meridiem:
        hour = hour % 12 + (12 if meridiem.upper() == "PM" else 0)

    offset = UTC_OFFSETS.get(rendered.split()[-1])
    if offset is None:
        return rendered

    moment = datetime(year, month, day, hour, int(minute), int(second))
    return (moment - timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_activity_controls(values):
    """The control names out of the localized "Why is this here?" sentence.

    They sit between the sentence's first colon and the following period. An
    entry that named no control has no such section at all, which is what
    keeps "no control named" detectable downstream.
    """
    sentence = " ".join(values)
    named = sentence.split(":", 1)[-1].split(".")[0]
    return [control.strip() for control in named.split(",") if control.strip()]


def parse_cell(cell):
    """One activity card as an entry dict."""
    entry = {}

    header = HEADER_RE.search(cell)
    if header:
        entry["header"] = unescape(header.group(1))

    body = BODY_RE.search(cell)
    lines = [line for line in body.group(1).split("<br>") if not is_blank(line)] if body else []

    if lines and TIME_RE.search(lines[-1]) and not LINK_RE.search(lines[-1]):
        entry["time"] = to_iso_utc(unescape(lines.pop()))
    if lines:
        title = lines.pop(0)
        entry["title"] = unescape(title)
        link = LINK_RE.search(title)
        if link:
            entry["titleUrl"] = html.unescape(link.group(1))
    if lines and "/channel/" in lines[0]:
        link = LINK_RE.search(lines.pop(0))
        entry["subtitles"] = [
            {"name": unescape(link.group(2)), "url": html.unescape(link.group(1))}
        ]
    if lines:
        entry["description"] = unescape(lines[0])

    caption = CAPTION_RE.search(cell)
    if caption:
        sections = SECTION_RE.split(caption.group(1))
        labelled = list(zip(sections[1::2], sections[2::2]))
        for index, (_label, block) in enumerate(labelled):
            # A stray space on "products" would fail the YouTube filter.
            values = [
                unescape(value).strip()
                for value in block.split("<br>")
                if not is_blank(value)
            ]
            if index == 0:
                entry["products"] = values
            elif index == len(labelled) - 1 and len(labelled) > 1:
                entry["activityControls"] = parse_activity_controls(values)
            else:
                entry["details"] = [{"name": value} for value in values]

    return entry


def iter_cells(chunks):
    """Yield each activity card from an iterable of text chunks.

    Cards are delimited by their opening div and the document's closing body,
    so a chunk boundary anywhere (including mid-delimiter) only ever leaves a
    partial card in `carry` for the next chunk to complete.
    """
    carry = ""
    open_card = False

    for chunk in chunks:
        pieces = (carry + chunk).split(CELL_START)
        if len(pieces) > 1:
            if open_card:
                yield CELL_START + pieces[0]
            for piece in pieces[1:-1]:
                yield CELL_START + piece
            open_card = True
        carry = pieces[-1]

    if open_card:
        yield CELL_START + carry.split("</body>")[0]


def parse_activity_html(source):
    """An entry dict for every activity card in an export's HTML."""
    return [parse_cell(cell) for cell in iter_cells([source])]


def read_activity_html(member):
    """The same, read off an open ZIP member a chunk at a time.

    `newline=""` because a title can contain a carriage return, which the
    default universal-newline translation would rewrite.
    """
    stream = io.TextIOWrapper(member, encoding="utf-8", newline="")
    chunks = iter(lambda: stream.read(CHUNK_SIZE), "")
    return [parse_cell(cell) for cell in iter_cells(chunks)]
