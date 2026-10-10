"""Post-deploy smoke test against a running ProtocolLedger service.

    uv run python scripts/smoke_test.py --base-url http://127.0.0.1:8001 \\
        --expect-model-version crf-logreg-4a9d8cc549

Checks health, readiness and the expected model version, a real extraction of the
worked example (evidence offsets and the implicit-object review item), the preview
endpoint, a full review round trip (create, read, export CSV) and the metrics endpoint.
Exits non-zero on the first failure. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

TEXT = "Example protocol\nAdd 5 mL of water to the tube, then mix for 30 s.\n"


def call(
    base: str, method: str, path: str, body: Any = None, headers: dict[str, str] | None = None
) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as res:
            raw = res.read().decode()
            kind = res.headers.get("content-type", "")
            return res.status, json.loads(raw) if "json" in kind else raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def check(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL {message}", file=sys.stderr)
        raise SystemExit(1)
    print(f"ok   {message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--expect-model-version", required=True)
    parser.add_argument("--skip-reviews", action="store_true")
    parser.add_argument("--skip-metrics", action="store_true")
    args = parser.parse_args(argv)
    base = args.base_url.rstrip("/")

    status, body = call(base, "GET", "/healthz")
    check(status == 200 and body == {"status": "ok"}, "healthz")
    status, body = call(base, "GET", "/readyz")
    check(status == 200, f"readyz ({status})")
    check(
        body["model_version"] == args.expect_model_version,
        f"model version {body['model_version']} == {args.expect_model_version}",
    )

    status, body = call(base, "POST", "/v1/extract", {"text": TEXT})
    check(status == 200, "extract")
    check(
        all(TEXT[e["start"] : e["end"]] == e["text"] for e in body["entities"]),
        "every entity's text is its raw-text slice",
    )
    check(any(e["label"] == "Action" for e in body["entities"]), "actions recognized")
    check(
        any("not explicitly stated" in i["issue"] for i in body["review_items"]),
        "implicit object routed to review",
    )

    content = {
        "entities": [
            {
                **{k: e[k] for k in ("id", "label", "start", "end")},
                "origin": "model",
                "decision": "accepted",
            }
            for e in body["entities"]
        ],
        "relations": [{**r, "origin": "model", "decision": "accepted"} for r in body["relations"]],
    }
    status, _ = call(base, "POST", "/v1/preview", {"text": TEXT, "content": content})
    check(status == 200, "preview")

    if not args.skip_reviews:
        status, created = call(
            base,
            "POST",
            "/v1/reviews",
            {
                "text": TEXT,
                "save_text": False,
                "model_version": args.expect_model_version,
                "content": content,
            },
        )
        check(status == 201 and created["token"], "create review")
        auth = {"X-Review-Token": created["token"]}
        status, record = call(base, "GET", f"/v1/reviews/{created['id']}", headers=auth)
        check(status == 200 and record["text"] is None, "read review (text not stored)")
        status, csv_text = call(
            base,
            "POST",
            f"/v1/reviews/{created['id']}/export",
            {"format": "csv", "text": TEXT},
            auth,
        )
        check(status == 200 and "review_status" in csv_text, "export CSV")

    if not args.skip_metrics:
        status, metrics = call(base, "GET", "/metrics")
        check(status == 200 and "protocolledger_model_info" in metrics, "metrics")
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
