import unittest
from pathlib import Path

from xml_rewriter import XmlRewriter


FIXTURES = Path(__file__).parent / "fixtures"


class XmlRewriterTests(unittest.TestCase):
    def test_rewrites_sample_feed(self):
        payload = (FIXTURES / "rewrite-sample.input.xml").read_bytes()
        expected = (FIXTURES / "rewrite-sample.output.xml").read_bytes().removesuffix(b"\n")

        rewritten = XmlRewriter({"title": "$title [$torrent:size]", "link": "$guid"}).rewrite(payload)

        self.assertEqual(expected, rewritten)

    def test_reuses_existing_element(self):
        payload = b"""<rss version=\"2.0\"><channel><item><title>Old</title><guid>abc</guid></item></channel></rss>"""

        rewritten = XmlRewriter({"title": "$title + extra"}).rewrite(payload)

        self.assertIn(b"<title>Old + extra</title>", rewritten)

    def test_excludes_items_with_matching_field_value(self):
        payload = (FIXTURES / "filter-sample.input.xml").read_bytes()
        expected = (FIXTURES / "filter-sample.output.xml").read_bytes().removesuffix(b"\n")

        rewritten = XmlRewriter(
            {},
            [{"field": "category", "values": ["Music Videos", "TV/SD"]}],
        ).rewrite(payload)

        self.assertEqual(expected, rewritten)


if __name__ == "__main__":
    unittest.main()
