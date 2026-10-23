from unittest.mock import patch

from app.jobs.tasks import run_maintenance_task


def test_run_maintenance_enqueues_all_sources_and_children():
    with patch("app.jobs.tasks.list_sources", return_value=["a", "b"]):
        with patch("app.jobs.tasks.collect_source_task") as mock_collect:
            with patch("app.jobs.tasks.expire_offers_task") as mock_expire:
                with patch("app.jobs.tasks.check_sources_health_task") as mock_health:
                    result = run_maintenance_task(123)

    assert mock_collect.defer.call_count == 2
    mock_collect.defer.assert_any_call(source_id="a")
    mock_collect.defer.assert_any_call(source_id="b")
    mock_expire.defer.assert_called_once()
    mock_health.defer.assert_called_once()
    assert result["sources"] == {"a": "enqueued", "b": "enqueued"}
    assert result["expired"] == "enqueued"
    assert result["health"] == "enqueued"


def test_run_maintenance_partial_failure_continues():
    def defer_side_effect(source_id=None, **kwargs):
        if source_id == "bad":
            raise RuntimeError("boom")
        return None

    with patch("app.jobs.tasks.list_sources", return_value=["good", "bad"]):
        with patch("app.jobs.tasks.collect_source_task") as mock_collect:
            mock_collect.defer.side_effect = defer_side_effect
            with patch("app.jobs.tasks.expire_offers_task") as mock_expire:
                mock_expire.defer.side_effect = RuntimeError("expire fail")
                with patch("app.jobs.tasks.check_sources_health_task") as mock_health:
                    result = run_maintenance_task(456)

    assert result["sources"]["good"] == "enqueued"
    assert result["sources"]["bad"].startswith("error:")
    assert result["expired"].startswith("error:")
    assert result["health"] == "enqueued"
    mock_health.defer.assert_called_once()