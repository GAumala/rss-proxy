# RSS Proxy

A small Python HTTP server that proxies RSS feeds and rewrites item fields using a TOML config.

## Config

Create `feeds.toml`:

```toml
[my-feed]
url = "https://example.com/upstream-feed.xml"
title = "$title $custom:field"
link = "$alt-link"

[[my-feed.exclude]]
field = "category"
values = ["Music Videos", "TV/SD"]
```

Each top-level TOML table becomes a route. `[my-feed]` is served at:

```text
http://localhost:8080/my-feed.xml
```

`url` is the upstream RSS feed. Any other key is treated as an item tag to rewrite. Template placeholders reference tags from the original item, including prefixed tags like `$custom:field`. If the feed declares a namespace URI, it is used; otherwise the prefix is treated as part of the literal tag name.

Use `[[feed-name.exclude]]` tables to remove items before rewriting. `field` is the item tag to inspect, and `values` is a list of exact trimmed text values to exclude.

`feeds.toml` is reloaded automatically when the file changes, and the in-memory per-feed cache is cleared on reload.

## Run

```sh
uv run rss-proxy --config feeds.toml --port 8080
```

Python 3.11+ is required for `tomllib`, and `uv` manages the `lxml` dependency.

```sh
uv sync
```

## Docker

Deploy by syncing the repo to the server, then building and running the container there. The server should already have its own `feeds.toml` in the mounted config directory.

```sh
docker build -t rss-proxy .
docker run -d --name rss-proxy --restart unless-stopped -v "$PWD:/config:ro" -p 8080:8080 rss-proxy
```

The container listens on `0.0.0.0:8080` inside Docker so the published port can receive traffic.

Do not push images built with a private `feeds.toml` to a public registry.

The server reloads `feeds.toml` automatically when the file changes and clears the in-memory feed cache on reload.

## Limits

Upstream feed responses are limited to 1 MiB. Rewritten feeds are cached in memory for 60 seconds per route.
