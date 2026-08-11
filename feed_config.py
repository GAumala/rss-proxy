import hashlib
import sys
import threading
import tomllib
from pathlib import Path


def load_config(path):
    return parse_config(path.read_bytes())


def parse_config(data):
    config = tomllib.loads(data.decode("utf-8"))

    feeds = {}
    for name, feed in config.items():
        if not isinstance(feed, dict):
            continue
        if "url" not in feed:
            raise ValueError(f"[{name}] is missing required 'url'")
        rewrites = {key: value for key, value in feed.items() if key not in {"url", "exclude"}}
        feeds[name] = {"url": feed["url"], "rewrites": rewrites, "exclude": feed.get("exclude", [])}
    return feeds


def config_digest(data):
    return hashlib.sha256(data).digest()


class FeedConfigManager:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._digest = None
        self._feeds = {}
        self.reload()

    @property
    def feeds(self):
        return self._feeds

    def reload(self):
        with self._lock:
            data = self.path.read_bytes()
            self._feeds = parse_config(data)
            self._digest = config_digest(data)

    def reload_if_changed(self, cache):
        with self._lock:
            try:
                data = self.path.read_bytes()
            except OSError as error:
                sys.stderr.write(f"config reload failed: {error}\n")
                return False

            current_digest = config_digest(data)
            if current_digest == self._digest:
                return False

            try:
                feeds = parse_config(data)
            except (UnicodeDecodeError, ValueError) as error:
                sys.stderr.write(f"config reload failed: {error}\n")
                return False

            self._feeds = feeds
            self._digest = current_digest
            cache.clear()
            sys.stderr.write(f"config reloaded: {len(feeds)} feed(s) loaded\n")
            return True
