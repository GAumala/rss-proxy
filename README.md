# RSS Proxy

A small Python HTTP server that proxies RSS feeds and rewrites item fields using a TOML config.

## Config

Create `feeds.toml`:

```toml
[my-feed]
url = "https://example.com/upstream-feed.xml"
title = "$title $custom:field"
link = "$alt-link"
```

Each top-level TOML table becomes a route. `[my-feed]` is served at:

```text
http://localhost:8080/my-feed.xml
```

`url` is the upstream RSS feed. Any other key is treated as an item tag to rewrite. Template placeholders reference tags from the original item, including prefixed tags like `$custom:field`. If the feed declares a namespace URI, it is used; otherwise the prefix is treated as part of the literal tag name.

## Run

```sh
uv run rss-proxy --config feeds.toml --port 8080
```

Python 3.11+ is required for `tomllib`, and `uv` manages the `lxml` dependency.

```sh
uv sync
```

## Docker

Create a local `feeds.toml` before building the image. This file is ignored by git but copied into the Docker image.

```sh
docker build -t rss-proxy .
docker run --rm -p 8080:8080 rss-proxy
```

The container listens on `0.0.0.0:8080` inside Docker so the published port can receive traffic.

Do not push images built with a private `feeds.toml` to a public registry.

## Limits

Upstream feed responses are limited to 256 KiB. Rewritten feeds are cached in memory for 60 seconds per route.
