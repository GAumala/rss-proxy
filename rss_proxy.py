#!/usr/bin/env python3
import argparse
import sys
import time
import tomllib
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lxml import etree as ET

from xml_rewriter import XmlRewriter


CACHE_TTL_SECONDS = 60
MAX_FEED_BYTES = 256 * 1024


def load_config(path):
    with path.open("rb") as config_file:
        config = tomllib.load(config_file)

    feeds = {}
    for name, feed in config.items():
        if not isinstance(feed, dict):
            continue
        if "url" not in feed:
            raise ValueError(f"[{name}] is missing required 'url'")
        rewrites = {key: value for key, value in feed.items() if key != "url"}
        feeds[name] = {"url": feed["url"], "rewrites": rewrites}
    return feeds


def fetch_feed(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "rss-proxy/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError(f"upstream feed exceeds {MAX_FEED_BYTES} bytes")
    return payload


def make_handler(feeds):
    cache = {}

    class RssProxyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            feed_name = self.path.lstrip("/").split("?", 1)[0]
            if feed_name.endswith(".xml"):
                feed_name = feed_name[:-4]

            feed = feeds.get(feed_name)
            if feed is None:
                self.send_error(404, "unknown feed")
                return

            try:
                cached = cache.get(feed_name)
                now = time.monotonic()
                if cached is None or now >= cached["expires_at"]:
                    payload = fetch_feed(feed["url"])
                    rewritten = XmlRewriter(feed["rewrites"]).rewrite(payload)
                    cached = {"payload": rewritten, "expires_at": now + CACHE_TTL_SECONDS}
                    cache[feed_name] = cached
                rewritten = cached["payload"]
            except urllib.error.URLError as error:
                self.send_error(502, f"upstream fetch failed: {error}")
                return
            except ET.XMLSyntaxError as error:
                self.send_error(502, f"upstream XML parse failed: {error}")
                return
            except ValueError as error:
                self.send_error(502, str(error))
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(rewritten)))
            self.end_headers()
            self.wfile.write(rewritten)

        def log_message(self, format, *args):
            sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    return RssProxyHandler


def main():
    parser = argparse.ArgumentParser(description="TOML-configured RSS feed rewrite proxy")
    parser.add_argument("--config", default="feeds.toml", type=Path, help="path to feeds TOML config")
    parser.add_argument("--host", default="127.0.0.1", help="host to bind")
    parser.add_argument("--port", default=8080, type=int, help="port to bind")
    args = parser.parse_args()

    feeds = load_config(args.config)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(feeds))
    print(f"Serving {len(feeds)} feed(s) on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
