"""Job that collects items from a registered source connector."""

from __future__ import annotations

from typing import Any

from app.sources.connector import get_connector


def collect_source(source_id: str) -> list[dict[str, Any]]:
    """Collect all items exposed by ``source_id``.

    Invokes the connector's ``lister_candidates`` then ``recuperer`` for each
    item. Every advertised job is collected, not only the ones whose title
    matches the channel theme: the catalogue is a reference set, and deciding
    what is worth publishing is the job of the extraction and scoring steps.

    Failures are recorded by the connector (counter + last error) and
    re-raised; they are never swallowed.
    """
    connector = get_connector(source_id)
    results: list[dict[str, Any]] = []
    for item in connector.lister_candidates():
        url = getattr(item, "url", None)
        if url is None and not isinstance(item, str):
            url = str(item)
        content = connector.recuperer(item)
        results.append(
            {
                "origin_url": url,
                "raw_text": content,
                "title": getattr(item, "title", None),
            }
        )
    return results
