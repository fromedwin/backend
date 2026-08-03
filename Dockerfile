FROM python:3.12-alpine

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /bin/uv

RUN adduser --disabled-password fromedwin

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Generate collectstatic folder to store static files
RUN mkdir /app/collectstatic
RUN chown fromedwin:fromedwin /app /app/collectstatic
VOLUME /app/collectstatic

# Copy dependency manifests first for better layer caching
COPY --chown=fromedwin pyproject.toml uv.lock /app/

# Install system dependencies and Python packages with uv
RUN \
    apk add --no-cache postgresql-libs libstdc++ tzdata nodejs npm curl && \
    apk add --no-cache --virtual .build-deps alpine-sdk postgresql-dev && \
    apk --update add build-base jpeg-dev zlib-dev libffi-dev && \
    uv sync --frozen --no-install-project --no-dev && \
    apk --purge del .build-deps && \
    chown -R fromedwin:fromedwin /app/.venv

# Add in docker image full code base
COPY --chown=fromedwin . .

# Ensure entrypoint script is executable
RUN chmod +x /app/src/entrypoint.sh

USER fromedwin
EXPOSE 8000
