"""Builders for Google activity HTML, mirroring the layout of the real exports."""

CAPTION_LABELS = {
    "de": ("Produkte:", "Details:", "Warum steht das hier?"),
    "en": ("Products:", "Details:", "Why is this here?"),
    "tr": ("Ürünler:", "Ayrıntılar:", "Bu neden burada?"),
}

WHY_SENTENCES = {
    "de": "Diese Aktivität wurde in Ihrem Google-Konto gespeichert, weil die folgenden Einstellungen aktiviert waren:&nbsp;{controls}.&nbsp;<a href=\"https://myaccount.google.com/activitycontrols\">Hier können Sie diese Einstellungen bearbeiten.</a>",
    "en": "This activity was saved to your Google Account because the following settings were on:&nbsp;{controls}.&nbsp;You can control these settings &nbsp;<a href=\"https://myaccount.google.com/activitycontrols\">here</a>.",
    "tr": "Bu etkinlik, aşağıdaki ayarlar etkin olduğu için Google Hesabınıza kaydedildi:&nbsp;{controls}.&nbsp;<a href=\"https://myaccount.google.com/activitycontrols\">Bu ayarları buradan kontrol edebilirsiniz.</a>",
}


def activity_cell(
    title,
    timestamp,
    *,
    header="YouTube",
    channel=None,
    description=None,
    products=("YouTube",),
    details=(),
    controls=(),
    locale="de",
):
    """One activity card. `controls=()` omits the "why" section, as Google does."""
    products_label, details_label, why_label = CAPTION_LABELS[locale]

    lines = [title]
    if channel:
        name, url = channel
        lines.append(f'<a href="{url}">{name}</a>')
    if description:
        lines.append(description)
    lines.append(timestamp)
    body = "<br>".join(lines) + "<br>"

    caption = f"<b>{products_label}</b><br>" + "".join(
        f"&emsp;{product}<br>" for product in products
    )
    if details:
        caption += f"<b>{details_label}</b><br>" + "".join(
            f"&emsp;{detail}<br>" for detail in details
        )
    if controls:
        sentence = WHY_SENTENCES[locale].format(controls=", ".join(controls))
        caption += f"<b>{why_label}</b><br>&emsp;{sentence}"

    return (
        '<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">'
        '<div class="mdl-grid">'
        '<div class="header-cell mdl-cell mdl-cell--12-col">'
        f'<p class="mdl-typography--title">{header}<br></p></div>'
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">'
        f"{body}</div>"
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1 '
        'mdl-typography--text-right"></div>'
        '<div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">'
        f"{caption}</div></div></div>"
    )


def activity_html(*cells):
    """An export document wrapping the given cells."""
    return (
        "<html><head><title>My Activity History</title>"
        "<style type=\"text/css\">.outer-cell{margin:0}</style></head>"
        '<body><div class="mdl-grid">' + "".join(cells) + "</div></body></html>"
    )


def watched_cell(video_id, title="Ein Video", **kwargs):
    kwargs.setdefault("channel", ("Ein Kanal", "https://www.youtube.com/channel/UCabc"))
    kwargs.setdefault("controls", ("YouTube-Wiedergabeverlauf",))
    return activity_cell(
        f'<a href="https://www.youtube.com/watch?v={video_id}">{title}</a> angesehen',
        "17.11.2026, 09:00:38 MEZ",
        **kwargs,
    )


def searched_cell(query, **kwargs):
    kwargs.setdefault("controls", ("YouTube-Suchverlauf",))
    return activity_cell(
        f'Gesucht nach:&nbsp;<a href="https://www.youtube.com/results?search_query={query}">{query}</a>',
        "20.10.2026, 17:29:49 MEZ",
        **kwargs,
    )


def subscribed_cell(channel_id, **kwargs):
    return activity_cell(
        f'<a href="https://www.youtube.com/channel/{channel_id}">Ein Kanal</a> abonniert',
        "07.05.2026, 00:44:26 MESZ",
        **kwargs,
    )
