"""Pick which items go into today's digest and group them into sections.

Rules (from the digest spec):
- each [[sources]] entry gives at most its `limit` items;
- items sent in the last 7 days are skipped, and so are repeats within one run;
- inside a source, items that show a count come before items that only show a rank;
- sources of the same platform share one section (two subreddits = one Reddit section);
- the whole digest holds at most `max_items` items; an empty section is left out and
  the other sections do not grow to fill its place.
"""

from .i18n import t
from .sources import TRACKED_METRIC, has_number, icon_url, platform_of


def add_deltas(items, yesterday):
    """Set the "+N today" delta from yesterday's snapshot, unless the API gave one."""
    for item in items:
        label = TRACKED_METRIC.get(item["extra"].get("platform"))
        old = yesterday.get(item["id"], {}).get("values", {})
        for m in item["metrics"]:
            if m["label"] != label or m["delta"] is not None or m["value"] is None:
                continue
            if label in old and m["value"] > old[label]:
                m["delta"] = m["value"] - old[label]


def pick_from_source(items, limit, skip_ids):
    """Up to `limit` new items, items with a count first, original order kept."""
    fresh = [item for item in items if item["id"] not in skip_ids]
    fresh.sort(key=lambda item: not has_number(item))
    return fresh[:limit]


def pick_items(fetched, skip_ids):
    """`fetched` = [(source_config, items)]. Returns [(source_config, picked)]."""
    taken = set(skip_ids)
    picks = []
    for source, items in fetched:
        chosen = pick_from_source(items, source["limit"], taken)
        taken.update(item["id"] for item in chosen)
        picks.append((source, chosen))
    return picks


def reddit_label(sources, lang):
    names = []
    for source in sources:
        if source["use"] == "reddit/trending_posts":
            names.append(t(lang, "section.reddit_trending"))
        elif source["params"].get("subreddit"):
            names.append("r/" + str(source["params"]["subreddit"]))
    base = t(lang, "section.reddit")
    return f"{base} · {', '.join(names)}" if names else base


def section_label(platform, sources, lang):
    """A section title such as 'Reddit · r/LocalLLaMA, r/MachineLearning'."""
    custom = next((s["label"] for s in sources if s["label"]), "")
    if custom:
        return custom
    if platform == "reddit":
        return reddit_label(sources, lang)
    if platform == "twitter":
        country = str(sources[0]["params"].get("country") or "us").upper()
        return t(lang, "section.twitter", country=country)
    if platform == "google_news" and len(sources) == 1 and sources[0]["params"].get("keyword"):
        return f'{t(lang, "section.google_news")} · "{sources[0]["params"]["keyword"]}"'
    return t(lang, f"section.{platform}")


def group_sections(picks, lang):
    """Merge picks of the same platform into sections, in config order."""
    order, grouped = [], {}
    for source, items in picks:
        platform = platform_of(source["use"])
        if platform not in grouped:
            order.append(platform)
            grouped[platform] = {"sources": [], "items": []}
        grouped[platform]["sources"].append(source)
        grouped[platform]["items"].extend(items)
    sections = []
    for platform in order:
        group = grouped[platform]
        if not group["items"]:
            continue
        icon = next((s["icon_url"] for s in group["sources"] if s["icon_url"]), "") or icon_url(platform)
        sections.append({"id": platform, "label": section_label(platform, group["sources"], lang),
                         "icon_url": icon, "items": group["items"]})
    return sections


def cap_total(sections, max_items):
    """Drop items from the end of the digest until it holds at most max_items."""
    total = sum(len(s["items"]) for s in sections)
    for section in reversed(sections):
        while total > max_items and section["items"]:
            section["items"].pop()
            total -= 1
    return [s for s in sections if s["items"]]


def all_items(sections):
    return [item for section in sections for item in section["items"]]
