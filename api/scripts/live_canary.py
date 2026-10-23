"""Live canary: check every source connector against the real websites.

Run it manually, never from CI: the job boards are third-party sites that can
be slow, rate-limited or temporarily down, and a CI failure caused by someone
else's outage is noise (T-019: "a canary test reports pass/fail separately
from CI").

Usage:
    uv run python scripts/live_canary.py
    uv run python scripts/live_canary.py --source emploiivoire
    uv run python scripts/live_canary.py --json

Exit codes:
    0  every source is reachable and parsing
    1  at least one source FAILED
    2  usage error

Verdicts:
    PASS      listing reachable, jobs parsed, detail page reachable
    DEGRADED  listing reachable and parsed, but no job matching the theme
              today. The site is healthy, it simply has nothing on-theme.
    FAIL      unreachable, robots-blocked, or the parser found no job at all
              (which means the site changed its markup).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.sources import connector as registry  # noqa: E402
from app.sources.base import USER_AGENT, BaseHttpConnector, Offer, match_theme  # noqa: E402

REQUEST_DELAY_SECONDS = 2.0


def _ascii(text: str) -> str:
    """Render text safely on any console encoding."""
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _http_status(url: str) -> tuple[int, int]:
    """Return (status_code, byte_count) for a URL, without following robots rules."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.status, len(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, 0
    except Exception:  # noqa: BLE001 - the canary reports failures, it never crashes
        return 0, 0


def check_source(source_id: str) -> dict[str, Any]:
    """Probe one source and return its canary report."""
    report: dict[str, Any] = {
        "source_id": source_id,
        "verdict": "FAIL",
        "reason": "",
        "robots_status": None,
        "listing_status": None,
        "listing_bytes": 0,
        "candidates": 0,
        "themed": 0,
        "detail_status": None,
        "samples": [],
    }

    wrapped = registry.get_connector(source_id)
    connector: BaseHttpConnector = wrapped._connector  # noqa: SLF001 - health wrapper

    report["robots_status"] = _http_status(f"{connector.base_url}/robots.txt")[0]

    try:
        html = connector._fetch(connector.base_url + connector.listing_path)  # noqa: SLF001
    except PermissionError as exc:
        report["reason"] = f"blocked by robots.txt: {exc}"
        return report
    except Exception as exc:  # noqa: BLE001
        report["reason"] = f"listing unreachable: {type(exc).__name__}: {exc}"
        return report

    report["listing_bytes"] = len(html)
    report["listing_status"] = 200

    try:
        candidates = connector.parse_candidates(html)
    except Exception as exc:  # noqa: BLE001
        report["reason"] = f"parser error: {type(exc).__name__}: {exc}"
        return report

    report["candidates"] = len(candidates)
    if not candidates:
        report["reason"] = "no job parsed: the site markup probably changed"
        return report

    themed = [o for o in candidates if match_theme(o.title)]
    report["themed"] = len(themed)
    report["samples"] = [
        {"title": o.title, "keyword": match_theme(o.title), "url": o.url}
        for o in (themed or candidates)[:5]
    ]

    probe: Offer | None = (themed or candidates)[0]
    status, size = _http_status(probe.url)
    report["detail_status"] = status
    report["detail_bytes"] = size

    if status == 0:
        report["reason"] = f"detail page unreachable: {probe.url}"
        return report

    if themed:
        report["verdict"] = "PASS"
    else:
        report["verdict"] = "DEGRADED"
        report["reason"] = "site healthy, no job matching the channel theme today"
    return report


def _print_table(reports: list[dict[str, Any]]) -> None:
    header = f"{'source':<16}{'verdict':<10}{'robots':>7}{'listing':>9}{'cands':>7}{'themed':>8}{'detail':>8}"
    print(header)
    print("-" * len(header))
    for report in reports:
        print(
            f"{report['source_id']:<16}{report['verdict']:<10}"
            f"{str(report['robots_status'] or '-'):>7}"
            f"{str(report['listing_status'] or report['listing_bytes'] or '-'):>9}"
            f"{report['candidates']:>7}{report['themed']:>8}"
            f"{str(report['detail_status'] or '-'):>8}"
        )
    print()
    for report in reports:
        print(f"[{report['verdict']}] {report['source_id']}")
        if report["reason"]:
            print(f"    {report['reason']}")
        for sample in report["samples"]:
            keyword = _ascii(sample["keyword"]) if sample["keyword"] else "-"
            print(f"    {keyword:<16} {_ascii(sample['title'][:66])}")
        print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live canary for the source connectors.")
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Only check this source id (repeatable). Defaults to all registered sources.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the report as JSON.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    import app.sources  # noqa: F401 - import registers the connectors

    source_ids = args.source or registry.list_sources()
    unknown = [s for s in source_ids if s not in registry.list_sources()]
    if unknown:
        print(f"Unknown source(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Known sources: {', '.join(registry.list_sources())}", file=sys.stderr)
        return 2

    reports: list[dict[str, Any]] = []
    for index, source_id in enumerate(source_ids):
        if index:
            time.sleep(REQUEST_DELAY_SECONDS)
        report = check_source(source_id)
        reports.append(report)

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        _print_table(reports)

    failed = [r for r in reports if r["verdict"] == "FAIL"]
    if failed:
        print(f"FAILED: {', '.join(r['source_id'] for r in failed)}", file=sys.stderr)
        return 1
    print("All sources reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
