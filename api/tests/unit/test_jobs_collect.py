from unittest.mock import patch

from app.jobs.collect_source import collect_source
from app.jobs.tasks import collect_source_task


def test_collect_source_invokes_lister_and_recuperer():
    class FakeConnector:
        def lister(self):
            return [type("Item", (), {"url": "http://x/1"})()]

        def recuperer(self, item):
            return f"content:{item.url}"

    from app.sources.connector import register, unregister, get_connector

    unregister("fake")
    register("fake", FakeConnector())
    wrapped = get_connector("fake")
    result = collect_source("fake")
    assert result == [{"origin_url": "http://x/1", "raw_text": "content:http://x/1"}]
    unregister("fake")


def test_collect_source_task_chains_extract(monkeypatch):
    with patch("app.jobs.tasks.collect_source", return_value=["raw text"]):
        with patch("app.jobs.tasks.extract_task.defer") as mock_defer:
            result = collect_source_task("src")
            assert result == ["raw text"]
            mock_defer.assert_called_once_with(raw_text="raw text", origin_url=None, source_id="src")