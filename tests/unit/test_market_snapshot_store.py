
from decimal import Decimal

import pytest

from app.storage.market_snapshot_store import MarketSnapshotStore


@pytest.fixture
def store(tmp_path):
    database_path = tmp_path / "data" / "test.sqlite3"
    snapshot_store = MarketSnapshotStore(database_path)
    snapshot_store.initialize()
    return snapshot_store


def make_snapshot(
    timestamp_ms=1_797_840_000_000,
    symbol="BTC/IDR",
    bid="1000000000",
    ask="1001000000",
    spread_pct="0.09995002498750624687656171914",
    quote_volume="500000000",
    net_profit_idr="-620",
    net_profit_pct="-0.62",
):
    return {
        "timestamp_ms": timestamp_ms,
        "exchange": "indodax",
        "symbol": symbol,
        "bid": Decimal(bid),
        "ask": Decimal(ask),
        "spread_pct": Decimal(spread_pct),
        "quote_volume_idr": Decimal(quote_volume),
        "net_profit_idr": Decimal(net_profit_idr),
        "net_profit_pct": Decimal(net_profit_pct),
    }


def test_initialize_creates_empty_snapshot_store(store):
    assert store.get_snapshots() == ()


def test_save_and_read_snapshot(store):
    snapshot = make_snapshot()

    count = store.save_snapshot(snapshot)
    result = store.get_snapshots()

    assert count == 1
    assert len(result) == 1
    assert result[0]["timestamp_ms"] == snapshot["timestamp_ms"]
    assert result[0]["exchange"] == "indodax"
    assert result[0]["symbol"] == "BTC/IDR"
    assert result[0]["bid"] == snapshot["bid"]
    assert result[0]["ask"] == snapshot["ask"]
    assert result[0]["net_profit_idr"] == snapshot["net_profit_idr"]
    assert result[0]["net_profit_pct"] == snapshot["net_profit_pct"]


def test_snapshots_for_same_symbol_are_not_overwritten(store):
    first = make_snapshot(timestamp_ms=1_797_840_000_000)
    second = make_snapshot(
        timestamp_ms=1_797_840_001_000,
        bid="1000000100",
        ask="1001000100",
    )

    store.save_snapshot(first)
    store.save_snapshot(second)

    result = store.get_snapshots(symbol="BTC/IDR")

    assert len(result) == 2
    assert result[0]["timestamp_ms"] < result[1]["timestamp_ms"]


def test_snapshots_can_be_filtered_by_symbol(store):
    store.save_snapshot(make_snapshot(symbol="BTC/IDR"))
    store.save_snapshot(
        make_snapshot(
            timestamp_ms=1_797_840_001_000,
            symbol="ETH/IDR",
        )
    )

    result = store.get_snapshots(symbol="ETH/IDR")

    assert len(result) == 1
    assert result[0]["symbol"] == "ETH/IDR"


def test_negative_profit_is_valid_snapshot_data(store):
    store.save_snapshot(make_snapshot(net_profit_idr="-620"))

    result = store.get_snapshots()

    assert result[0]["net_profit_idr"] == Decimal("-620")


@pytest.mark.parametrize(
    "overrides",
    [
        {"timestamp_ms": 0},
        {"timestamp_ms": True},
        {"exchange": ""},
        {"symbol": ""},
        {"bid": Decimal("0")},
        {"bid": Decimal("-1")},
        {"bid": Decimal("NaN")},
        {"ask": Decimal("0")},
        {"ask": Decimal("NaN")},
        {"spread_pct": Decimal("-1")},
        {"spread_pct": Decimal("Infinity")},
        {"quote_volume_idr": Decimal("-1")},
        {"net_profit_idr": Decimal("NaN")},
        {"net_profit_pct": Decimal("Infinity")},
    ],
)
def test_invalid_snapshot_is_rejected(store, overrides):
    snapshot = make_snapshot()
    snapshot.update(overrides)

    with pytest.raises(ValueError):
        store.save_snapshot(snapshot)

    assert store.get_snapshots() == ()


def test_ask_below_bid_is_rejected(store):
    snapshot = make_snapshot(
        bid="1001000000",
        ask="1000000000",
    )

    with pytest.raises(ValueError):
        store.save_snapshot(snapshot)


def test_invalid_limit_is_rejected(store):
    with pytest.raises(ValueError, match="limit minimal 1"):
        store.get_snapshots(limit=0)


def test_limit_returns_most_recent_snapshots_in_chronological_order(store):
    first = make_snapshot(timestamp_ms=1_797_840_000_000)
    second = make_snapshot(
        timestamp_ms=1_797_840_001_000,
        bid="1000000100",
        ask="1001000100",
    )
    third = make_snapshot(
        timestamp_ms=1_797_840_002_000,
        bid="1000000200",
        ask="1001000200",
    )

    store.save_snapshot(first)
    store.save_snapshot(second)
    store.save_snapshot(third)

    result = store.get_snapshots(limit=2)

    assert len(result) == 2
    assert [
        item["timestamp_ms"] for item in result
    ] == [
        second["timestamp_ms"],
        third["timestamp_ms"],
    ]


def test_limit_returns_most_recent_snapshots_for_symbol(store):
    store.save_snapshot(
        make_snapshot(
            timestamp_ms=1_797_840_000_000,
            symbol="BTC/IDR",
        )
    )
    store.save_snapshot(
        make_snapshot(
            timestamp_ms=1_797_840_001_000,
            symbol="ETH/IDR",
        )
    )
    store.save_snapshot(
        make_snapshot(
            timestamp_ms=1_797_840_002_000,
            symbol="BTC/IDR",
        )
    )

    result = store.get_snapshots(
        symbol="BTC/IDR",
        limit=1,
    )

    assert len(result) == 1
    assert result[0]["timestamp_ms"] == 1_797_840_002_000

