import pytest

from app.jobs.collect_source import collect_source
from app.sources.base import Offer
from app.sources.connector import (
    ConnectorHealth,
    RegisteredConnector,
    SourceConnector,
    get_connector,
    list_sources,
    register,
    unregister,
)


class FakeConnector:
    source_id = "fake"

    def __init__(self):
        self.lister_calls = 0
        self.health_result = {"status": "ok"}

    def lister(self):
        self.lister_calls += 1
        return ["a", "b"]

    def recuperer(self, item):
        return item.upper()

    def sante(self):
        return dict(self.health_result)


def test_source_connector_is_runtime_checkable():
    assert isinstance(FakeConnector(), SourceConnector)


def test_register_and_get_connector_instance():
    unregister("fake")
    conn = FakeConnector()
    register("fake", conn)
    assert "fake" in list_sources()
    wrapped = get_connector("fake")
    assert isinstance(wrapped, RegisteredConnector)
    assert wrapped.source_id == "fake"
    unregister("fake")


def test_register_factory():
    unregister("fake")
    register("fake", FakeConnector)
    wrapped = get_connector("fake")
    assert isinstance(wrapped, RegisteredConnector)
    # health persists across calls
    wrapped2 = get_connector("fake")
    assert wrapped2 is wrapped
    unregister("fake")


def test_collect_source_invokes_lister_and_recuperer():
    unregister("fake")
    register("fake", FakeConnector())
    result = collect_source("fake")
    # collect_source returns one record per collected item, carrying the
    # origin URL and the raw content, so that the job can persist it.
    assert result == [
        {"origin_url": None, "raw_text": "A"},
        {"origin_url": None, "raw_text": "B"},
    ]
    unregister("fake")


def test_collect_source_carries_the_origin_url_of_offered_items():
    unregister("fake")

    class UrlConnector(FakeConnector):
        def lister(self):
            return [Offer(url="https://example.com/job/1", title="Job")]

    register("fake", UrlConnector())
    result = collect_source("fake")
    assert result == [{"origin_url": "https://example.com/job/1", "raw_text": "JOB"}]
    unregister("fake")


def test_failure_is_recorded_and_propagated():
    unregister("fake")

    class FailingConnector(FakeConnector):
        def lister(self):
            raise ValueError("boom")

    register("fake", FailingConnector())
    wrapped = get_connector("fake")
    with pytest.raises(ValueError):
        collect_source("fake")
    assert wrapped.health.failure_count == 1
    assert wrapped.health.last_error is not None
    assert "ValueError" in wrapped.health.last_error
    assert wrapped.health.last_failure_at is not None
    unregister("fake")


def test_recuperer_failure_recorded():
    unregister("fake")

    class FailingRecuperer(FakeConnector):
        def recuperer(self, item):
            raise RuntimeError("nope")

    register("fake", FailingRecuperer())
    wrapped = get_connector("fake")
    with pytest.raises(RuntimeError):
        collect_source("fake")
    assert wrapped.health.failure_count == 1
    unregister("fake")


def test_sante_reports_health_success():
    unregister("fake")
    register("fake", FakeConnector())
    wrapped = get_connector("fake")
    health = wrapped.sante()
    assert health["source_id"] == "fake"
    assert health["status"] == "ok"
    assert health["failure_count"] == 0
    assert health["last_success_at"] is not None
    unregister("fake")


def test_sante_swallows_exception_for_reporting():
    unregister("fake")

    class BadHealth(FakeConnector):
        def sante(self):
            raise RuntimeError("health boom")

    register("fake", BadHealth())
    wrapped = get_connector("fake")
    health = wrapped.sante()  # must not raise
    assert health["status"] == "unhealthy"
    assert health["failure_count"] == 1
    assert "RuntimeError" in (health["last_error"] or "")
    unregister("fake")


def test_get_connector_unknown_raises_keyerror():
    unregister("nope")
    with pytest.raises(KeyError):
        get_connector("nope")


def test_unregister():
    unregister("fake")
    register("fake", FakeConnector())
    assert "fake" in list_sources()
    unregister("fake")
    assert "fake" not in list_sources()