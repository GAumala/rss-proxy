FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
COPY rss_proxy.py xml_rewriter.py feed_config.py ./

RUN uv sync --frozen --no-dev --no-cache

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["uv", "run", "--frozen", "rss-proxy", "--config", "/config/feeds.toml", "--host", "0.0.0.0", "--port", "8080"]
