import tempfile
import unittest
from pathlib import Path

from feed_config import FeedConfigManager, load_config


class RssProxyTests(unittest.TestCase):
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
