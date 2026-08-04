"""Minimal Prometheus HTTP API client for PromQL queries."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return settings.PROMETHEUS_URL.rstrip("/")


def query(promql: str, timeout: int = 10) -> list[dict[str, Any]]:
    """Run an instant PromQL query. Returns Prometheus `data.result` list."""
    try:
        response = requests.get(
            f"{_base_url()}/api/v1/query",
            params={"query": promql},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.error("Prometheus query failed: %s (%s)", promql, exc)
        return []

    if payload.get("status") != "success":
        logger.error("Prometheus query error: %s — %s", promql, payload)
        return []

    return payload.get("data", {}).get("result", [])


def query_range(
    promql: str,
    start: datetime,
    end: datetime,
    step: str = "60s",
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Run a range PromQL query. Returns Prometheus `data.result` list."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    try:
        response = requests.get(
            f"{_base_url()}/api/v1/query_range",
            params={
                "query": promql,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": step,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.error("Prometheus query_range failed: %s (%s)", promql, exc)
        return []

    if payload.get("status") != "success":
        logger.error("Prometheus query_range error: %s — %s", promql, payload)
        return []

    return payload.get("data", {}).get("result", [])


def instant_value(promql: str, default=None):
    """Return the numeric value of the first instant-query series, or default."""
    results = query(promql)
    if not results:
        return default
    try:
        return float(results[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return default
