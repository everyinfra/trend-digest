"""Telegram Bot API `sendMessage` body (without chat_id, which `send` adds).

One message with `parse_mode: "HTML"`, link previews off, and two URL buttons
in `reply_markup.inline_keyboard`. The text must be at most 4,096 characters
(Telegram counts after parsing the tags; we count the raw text, which is never
shorter, so we stay under). When it is too long, items are removed rather than
splitting it into several messages.

Telegram's HTML mode accepts only a few tags (b, i, a, ...) and needs <, > and
& written as &lt; &gt; &amp; everywhere else.
"""

import html

from .common import links_for, shrink_until, utf16_size, why_label

MAX_TEXT = 4096


def esc(text):
    return html.escape(text or "", quote=True)


def item_lines(number, item, why):
    head = f'{number}. <a href="{esc(item["url"])}">{esc(item["title"])}</a>'
    if item.get("metric_text"):
        head += f" · {esc(item['metric_text'])}"
    lines = [head]
    if item.get("summary"):
        lines.append(esc(item["summary"]))
    if item.get("why"):
        lines.append(f"<i>{esc(why)}:</i> {esc(item['why'])}")
    return "\n".join(lines)


def build(message):
    why = why_label(message)
    parts = [f"<b>{esc(message['title'])}</b>"]
    if message.get("subtitle"):
        parts[0] += "\n" + esc(message["subtitle"])
    for section in message["sections"]:
        lines = [f"<b>{esc(section['label'])}</b>"]
        lines += [item_lines(n, item, why) for n, item in enumerate(section["items"], 1)]
        parts.append("\n".join(lines))
    links = links_for(message, "telegram")
    parts.append(esc(message["footer"]) + "\n" +
                 " · ".join(f'<a href="{esc(url)}">{esc(label)}</a>' for label, url in links))
    return {
        "text": "\n\n".join(parts),
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
        "reply_markup": {"inline_keyboard": [[{"text": label, "url": url} for label, url in links]]},
    }


def fits(body):
    return utf16_size(body["text"]) <= MAX_TEXT


def render(message):
    return shrink_until(message, build, fits)
