
import pytest

from app.storage.scan_diagnostics_store import ScanDiagnosticsStore


@pytest.fixture
def store(tmp_path):
    instance = ScanDiagnosticsStore(
        tmp_path / "scan_diagnostics.sqlite3"
    )
    instance.initialize()
    return instance


def make_run(**overrides):
    run = {
        "started_at_ms": 1000,
        "finished_at_ms": 1500,
        "duration_ms": 500,
        "status": "completed",
        "candidates_found": 10,
        "order_books_attempted": 5,
        "order_books_failed": 1,
        "invalid_order_books": 1,
        "invalid_market_metadata": 0,
        "insufficient_depth": 1,
        "estimation_errors": 0,
        "below_profit_target": 1,
        "profitable_candidates": 1,
        "snapshots_saved": 4,
        "snapshot_save_failures": 0,
        "error_type": None,
        "error_message": None,
    }
    run.update(overrides)
    return run


def test_initialize_creates_empty_store(store):
    assert store.get_runs() == ()


def test_save_and_read_scan_run(store):
    run = make_run()

    run_id = store.save_run(run)
    result = store.get_runs()

    assert run_id == 1
    assert len(result) == 1
    assert result[0]["status"] == "completed"
    assert result[0]["candidates_found"] == 10
    assert result[0]["profitable_candidates"] == 1
    assert result[0]["duration_ms"] == 500


def test_failed_scan_can_be_recorded(store):
    run = make_run(
        status="failed",
        error_type="ConnectionError",
        error_message="Exchange tidak dapat dihubungi.",
    )

    store.save_run(run)

    result = store.get_runs(status="failed")

    assert len(result) == 1
    assert result[0]["error_type"] == "ConnectionError"
    assert result[0]["error_message"] == (
        "Exchange tidak dapat dihubungi."
    )


def test_completed_scan_does_not_keep_error(store):
    run = make_run(
        error_type="OldError",
        error_message="Pesan lama",
    )

    store.save_run(run)

    result = store.get_runs()[0]

    assert result["error_type"] is None
    assert result["error_message"] is None


def test_limit_returns_most_recent_runs_in_chronological_order(store):
    store.save_run(make_run(
        started_at_ms=1000,
        finished_at_ms=1500,
        duration_ms=500,
    ))
    store.save_run(make_run(
        started_at_ms=2000,
        finished_at_ms=2500,
        duration_ms=500,
    ))
    store.save_run(make_run(
        started_at_ms=3000,
        finished_at_ms=3500,
        duration_ms=500,
    ))

    result = store.get_runs(limit=2)

    assert [
        run["started_at_ms"] for run in result
    ] == [2000, 3000]


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_limit_is_rejected(store, limit):
    with pytest.raises(ValueError):
        store.get_runs(limit=limit)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidates_found", -1),
        ("duration_ms", -1),
        ("started_at_ms", True),
        ("profitable_candidates", 1.5),
    ],
)
def test_invalid_counter_or_timestamp_is_rejected(
    store,
    field,
    value,
):
    with pytest.raises(ValueError):
        store.save_run(make_run(**{field: value}))


def test_finish_time_before_start_time_is_rejected(store):
    with pytest.raises(ValueError):
        store.save_run(make_run(
            started_at_ms=2000,
            finished_at_ms=1000,
            duration_ms=0,
        ))


def test_inconsistent_duration_is_rejected(store):
    with pytest.raises(ValueError):
        store.save_run(make_run(duration_ms=100))


def test_invalid_status_is_rejected(store):
    with pytest.raises(ValueError):
        store.save_run(make_run(status="unknown"))


def test_status_filter_returns_only_matching_runs(store):
    store.save_run(make_run(
        started_at_ms=1000,
        finished_at_ms=1500,
        duration_ms=500,
        status="completed",
    ))
    store.save_run(make_run(
        started_at_ms=2000,
        finished_at_ms=2500,
        duration_ms=500,
        status="failed",
        error_type="RuntimeError",
        error_message="Test error",
    ))

    result = store.get_runs(status="completed")

    assert len(result) == 1
    assert result[0]["status"] == "completed"
