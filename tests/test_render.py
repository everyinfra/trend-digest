"""Channel bodies stay within each service's limits; HTML is escaped."""

import unittest
from html.parser import HTMLParser

from helpers import at, default_config_path, fixture_fetch

from trend_digest import build_digest
from trend_digest.render import discord, html, slack, telegram, wecom


def long_message(sections=9, items=12, text="word ", lang="en"):
    """A message far over every limit."""
    return {
        "lang": lang, "title": "Big digest", "subtitle": "Today: a · b · c",
        "footer": "Data via EveryInfra · 6 API calls · $0.005 today", "site_url": "https://example.github.io/td/",
        "sections": [{
            "id": f"s{s}", "label": f"Section {s}", "icon_url": "https://example.com/i.png",
            "items": [{"id": f"x:{s}-{i}", "title": text * 30, "url": f"https://example.com/{s}/{i}",
                       "summary": text * 40, "metric_text": "★ 1,000", "why": "short reason",
                       "extra": {}} for i in range(items)],
        } for s in range(sections)],
    }


def item_count(message_sections):
    return sum(len(s["items"]) for s in message_sections)


class DiscordTest(unittest.TestCase):
    def setUp(self):
        self.body = build_digest(default_config_path(), fetch=fixture_fetch(),
                                 now=at("2026-11-24"))["payloads"]["discord"][0]

    def test_shape_and_limits(self):
        embeds = self.body["embeds"]
        self.assertLessEqual(len(embeds), 10)
        self.assertLessEqual(sum(discord.embed_text_size(e) for e in embeds), 6000)
        urls = [e["url"] for e in embeds]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(self.body["allowed_mentions"], {"parse": []})
        self.assertNotIn("content", self.body)
        self.assertEqual(set(self.body), {"embeds", "components", "allowed_mentions"})

    def test_title_keywords_footer_and_buttons(self):
        first, last = self.body["embeds"][0], self.body["embeds"][-1]
        self.assertTrue(first["title"].startswith("EveryInfra Trend Digest"))
        self.assertTrue(first["description"].startswith("Today: "))
        self.assertIn("Data via EveryInfra", last["footer"]["text"])
        self.assertIn("[Run your own digest](https://github.com/everyinfra/trend-digest?utm_source=discord-digest)",
                      last["description"])
        buttons = self.body["components"][0]["components"]
        self.assertEqual([b["style"] for b in buttons], [5])
        self.assertEqual(self.body["embeds"][1]["author"]["name"], "GitHub trending")

    def test_too_long_input_loses_items_until_it_fits(self):
        message = long_message()
        body = discord.render(message)
        self.assertTrue(discord.fits(body))
        shown = sum(e.get("description", "").count("](https://example.com/") for e in body["embeds"])
        self.assertLess(shown, item_count(message["sections"]))
        self.assertGreater(shown, 0)


class TelegramTest(unittest.TestCase):
    def test_escaped_and_one_message_under_4096(self):
        message = long_message(text="<b>A&B</b> ")
        body = telegram.render(message)
        self.assertLessEqual(len(body["text"].encode("utf-16-le")) // 2, 4096)
        self.assertNotIn("<b>A&B</b>", body["text"])
        self.assertIn("&lt;b&gt;A&amp;B&lt;/b&gt;", body["text"])
        self.assertEqual(body["parse_mode"], "HTML")
        self.assertEqual(len(body["reply_markup"]["inline_keyboard"][0]), 2)

    def test_daily_list_has_one_telegram_message(self):
        digest = build_digest(default_config_path(), fetch=fixture_fetch(), now=at("2026-11-24"))
        self.assertEqual(len(digest["payloads"]["telegram"]), 1)


class WecomTest(unittest.TestCase):
    def test_content_under_4096_bytes(self):
        body = wecom.render(long_message(text="中文标题 ", lang="zh"))
        self.assertLessEqual(len(body["markdown"]["content"].encode("utf-8")), 4096)
        self.assertEqual(body["msgtype"], "markdown")


class SlackTest(unittest.TestCase):
    def test_block_and_text_limits(self):
        body = slack.render(long_message(sections=30, items=12))
        self.assertLessEqual(len(body["blocks"]), 50)
        for block in body["blocks"]:
            if block["type"] == "section":
                self.assertLessEqual(len(block["text"]["text"]), 3000)
        self.assertTrue(body["text"])


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.hrefs = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.hrefs += [v for k, v in attrs if k == "href"]


class HtmlTest(unittest.TestCase):
    def data(self):
        return {"date": "2026-11-24", "language": "en", "title": "Digest <script>alert(1)</script>",
                "keywords": ["<script>"], "weekly": None, "usage": {"calls": 6, "charged_usd": 0.004},
                "sections": [{"id": "github", "label": "GitHub trending", "items": [
                    {"title": "<script>alert('x')</script>", "url": "javascript:alert(1)",
                     "summary": "a & b", "metric_text": "★ 1", "why": None},
                    {"title": "ok", "url": "https://example.com/ok", "summary": "", "metric_text": "", "why": None}]}]}

    def test_script_escaped_and_javascript_link_dropped(self):
        page = html.day_page(self.data())
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("javascript:", page)
        parser = Collector()
        parser.feed(page)
        self.assertNotIn("script", parser.tags)
        self.assertIn("https://example.com/ok", parser.hrefs)

    def test_page_has_title_description_and_og(self):
        page = html.day_page(self.data())
        for needle in ("<title>", '<meta name="description"', 'property="og:title"', "../assets/style.css"):
            self.assertIn(needle, page)


if __name__ == "__main__":
    unittest.main()
