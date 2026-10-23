"""Common source connector interface, health tracking and registry.

A source connector exposes three operations:
- ``lister``: enumerate available items from the source.
- ``recuperer``: fetch the content of a single item.
- ``sante``: report the health of the source.

Connectors are registered through :func:`register` (directly or as a decorator)
so that a new source can be added with one module plus one registry line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class SourceConnector(Protocol):
    """Minimal contract every source connector must satisfy."""

    source_id: str

    def lister(self) -> list[Any]:
        """Return the list of items available on the source."""

    def recuperer(self, item: Any) -> Any:
        """Fetch and return the content of ``item``."""

    def sante(self) -> dict[str, Any]:
        """Report the health of the source."""

    def parse_detail(self, html: str) -> Any:
        """Extract the structured fields of a detail page."""


@dataclass
class ConnectorHealth:
    """Mutable health state tracked for a registered connector."""

    failure_count: int = 0
    last_error: str | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None


class RegisteredConnector:
    """Wrapper that delegates to a connector and tracks failures.

    Failures are recorded (counter + last error) but never swallowed: the
    original exception is re-raised so callers can react.
    """

    def __init__(self, source_id: str, connector: SourceConnector) -> None:
        self.source_id = source_id
        self._connector = connector
        self.health = ConnectorHealth()

    def _record_success(self) -> None:
        self.health.last_success_at = datetime.now(timezone.utc)
        self.health.last_error = None

    def _record_failure(self, exc: Exception) -> None:
        self.health.failure_count += 1
        self.health.last_error = f"{type(exc).__name__}: {exc}"
        self.health.last_failure_at = datetime.now(timezone.utc)

    def lister(self) -> list[Any]:
        try:
            result = self._connector.lister()
        except Exception as exc:  # noqa: BLE001 - record then re-raise
            self._record_failure(exc)
            raise
        self._record_success()
        return result

    def recuperer(self, item: Any) -> Any:
        try:
            result = self._connector.recuperer(item)
        except Exception as exc:  # noqa: BLE001 - record then re-raise
            self._record_failure(exc)
            raise
        self._record_success()
        return result

    def lister_candidates(self) -> list[Any]:
        try:
            result = self._connector.lister_candidates()
        except Exception as exc:  # noqa: BLE001 - record then re-raise
            self._record_failure(exc)
            raise
        self._record_success()
        return result

    def listing_pages(self) -> list[list[str]]:
        """The listing pages the connector reads, grouped by search term.

        Exposed by the wrapper so that a caller can report what a collection
        is about to read without reading it.
        """
        pages = getattr(self._connector, "listing_pages", None)
        if pages is None:
            return []
        return pages()

    def parse_detail(self, html: str) -> Any:
        """Extract the structured fields of a detail page."""
        parse = getattr(self._connector, "parse_detail", None)
        if parse is None:
            raise NotImplementedError(
                f"connector {self.source_id} does not implement parse_detail"
            )
        return parse(html)

    def sante(self) -> dict[str, Any]:
        """Report health. Connector errors are swallowed here on purpose so
        that a health probe never crashes the caller; they are recorded in
        health state. Other operations (lister/recuperer) propagate."""
        base: dict[str, Any] = {}
        try:
            base = dict(self._connector.sante() or {})
            # A successful health check counts as a success for tracking.
            self._record_success()
        except Exception as exc:  # noqa: BLE001 - report degraded health (swallowed on purpose for health reporting; other ops propagate)
            self._record_failure(exc)
            base = {"status": "unhealthy"}
        return {
            "source_id": self.source_id,
            "failure_count": self.health.failure_count,
            "last_error": self.health.last_error,
            "last_success_at": (
                self.health.last_success_at.isoformat()
                if self.health.last_success_at
                else None
            ),
            "last_failure_at": (
                self.health.last_failure_at.isoformat()
                if self.health.last_failure_at
                else None
            ),
            **base,
        }


# Registry of registered connectors (or factories producing them).
_REGISTRY: dict[str, Callable[[], SourceConnector] | SourceConnector] = {}


def register(
    source_id: str,
    connector: Any = None,
) -> Any:
    """Register a source connector.

    Usages:
    - ``register("rss", RssConnector)`` with a class/factory.
    - ``register("rss", instance)`` with an instance.
    - ``@register("rss")`` as a decorator on a connector class.
    """

    def _store(factory_or_instance: Any) -> Any:
        _REGISTRY[source_id] = factory_or_instance
        return factory_or_instance

    if connector is None:
        return _store

    return _store(connector)


def get_connector(source_id: str) -> RegisteredConnector:
    """Resolve a registered source id into a tracked connector instance."""
    if source_id not in _REGISTRY:
        raise KeyError(f"unknown source connector: {source_id}")
    entry = _REGISTRY[source_id]
    # If the entry is a class/factory (or any callable that is not already a
    # connector instance), invoke it to obtain an instance. Otherwise use as-is.
    is_factory = isinstance(entry, type) or (callable(entry) and not isinstance(entry, SourceConnector))
    connector: SourceConnector
    if is_factory and callable(entry):
        connector = entry()
    else:
        connector = entry  # type: ignore[assignment]
    if not isinstance(connector, RegisteredConnector):
        connector = RegisteredConnector(source_id, connector)
    # Keep the tracked instance in the registry so health persists.
    _REGISTRY[source_id] = connector
    return connector


def list_sources() -> list[str]:
    """Return the ids of all registered sources."""
    return sorted(_REGISTRY.keys())


def unregister(source_id: str) -> None:
    """Remove a source from the registry (useful for tests)."""
    _REGISTRY.pop(source_id, None)
