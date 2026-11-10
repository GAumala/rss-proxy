import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from feed_config import FeedConfigManager, load_config
from rss_proxy import MAX_FEED_BYTES, fetch_feed


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, size):
        return self.payload[:size]


class RssProxyTests(unittest.TestCase):
    @patch("rss_proxy.urllib.request.urlopen")
    def test_fetch_feed_accepts_feeds_above_the_old_512_kib_limit(self, urlopen):
        payload = b"x" * (512 * 1024 + 1)
        urlopen.return_value = FakeResponse(payload)

        self.assertEqual(payload, fetch_feed("https://example.com/feed.xml"))

    @patch("rss_proxy.urllib.request.urlopen")
    def test_fetch_feed_rejects_feeds_above_the_limit(self, urlopen):
        urlopen.return_value = FakeResponse(b"x" * (MAX_FEED_BYTES + 1))

        with self.assertRaisesRegex(ValueError, f"exceeds {MAX_FEED_BYTES} bytes"):
            fetch_feed("https://example.com/feed.xml")

    def test_load_config_keeps_exclude_separate_from_rewrites(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "feeds.toml"
            config_path.write_text(
                """
[my-feed]
url = "https://example.com/feed.xml"
title = "$title"

[[my-feed.exclude]]
field = "category"
values = ["Music Videos", "TV/SD"]
""".lstrip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual("https://example.com/feed.xml", config["my-feed"]["url"])
        self.assertEqual({"title": "$title"}, config["my-feed"]["rewrites"])
        self.assertEqual(
            [{"field": "category", "values": ["Music Videos", "TV/SD"]}],
            config["my-feed"]["exclude"],
        )

    def test_reload_config_if_changed_adds_new_feeds_and_clears_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "feeds.toml"
            config_path.write_text(
                """
[my-feed]
url = "https://example.com/feed.xml"
title = "$title"
""".lstrip(),
                encoding="utf-8",
            )

            manager = FeedConfigManager(config_path)
            cache = {"my-feed": {"payload": b"cached", "expires_at": 12345}}

            config_path.write_text(
                """
[my-feed]
url = "https://example.com/feed.xml"
title = "$title"
link = "$guid"

[new-feed]
url = "https://example.com/new-feed.xml"
title = "$title"
""".lstrip(),
                encoding="utf-8",
            )

            reloaded = manager.reload_if_changed(cache)

        self.assertTrue(reloaded)
        self.assertEqual({"title": "$title", "link": "$guid"}, manager.feeds["my-feed"]["rewrites"])
        self.assertEqual("https://example.com/new-feed.xml", manager.feeds["new-feed"]["url"])
        self.assertEqual({}, cache)


if __name__ == "__main__":
    unittest.main()
