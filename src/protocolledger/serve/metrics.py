"""Prometheus metrics for the service (one registry per app instance).

Route labels use the matched route template (``/v1/reviews/{review_id}``), never the
raw path, so label cardinality stays bounded. No metric carries submitted text.
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    ProcessCollector,
)

_SIZE_BUCKETS = (100, 500, 1_000, 2_500, 5_000, 10_000, 20_000)
_COUNT_BUCKETS = (0, 1, 5, 10, 25, 50, 100, 250, 500, 1_000)
_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 10)


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        ProcessCollector(registry=self.registry)  # RSS, CPU, open fds (Linux)
        r = self.registry
        self.requests = Counter(
            "protocolledger_http_requests",
            "HTTP requests.",
            ["method", "route", "status"],
            registry=r,
        )
        self.latency = Histogram(
            "protocolledger_http_request_seconds",
            "Request latency.",
            ["route"],
            buckets=_LATENCY_BUCKETS,
            registry=r,
        )
        self.in_flight = Gauge(
            "protocolledger_http_in_flight", "Requests currently being processed.", registry=r
        )
        self.input_chars = Histogram(
            "protocolledger_extract_input_chars",
            "Characters per extraction request.",
            buckets=_SIZE_BUCKETS,
            registry=r,
        )
        self.entities = Histogram(
            "protocolledger_extract_entities",
            "Entities per extraction.",
            buckets=_COUNT_BUCKETS,
            registry=r,
        )
        self.relations = Histogram(
            "protocolledger_extract_relations",
            "Relations per extraction.",
            buckets=_COUNT_BUCKETS,
            registry=r,
        )
        self.review_items = Histogram(
            "protocolledger_extract_review_items",
            "Items routed to review per extraction.",
            buckets=_COUNT_BUCKETS,
            registry=r,
        )
        self.entity_labels = Counter(
            "protocolledger_predicted_entities",
            "Predicted entities by label.",
            ["label"],
            registry=r,
        )
        self.review_operations = Counter(
            "protocolledger_review_operations",
            "Review store operations.",
            ["operation"],
            registry=r,
        )
        self.review_decisions = Counter(
            "protocolledger_review_decisions",
            "Entity and relation decisions in submitted reviews (correction rates).",
            ["kind", "origin", "decision"],
            registry=r,
        )
        self.model_info = Gauge(
            "protocolledger_model_info",
            "Loaded model (value is always 1).",
            ["model_version", "system", "bundle_sha256"],
            registry=r,
        )
