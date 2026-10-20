
import pytest

from app.domain.candle import Candle
from app.storage.database import CandleStore


BASE_TS = 1_797_840_000_000


def make_candle(
    timestamp_ms=BASE_TS,
    close=105.0,
    volume=12.0,
):
    return Candle(
        exchange="indodax",
        symbol="ETH/USDT",
        timeframe="15m",
        timestamp_ms=timestamp_ms,
        open=100.0,
        high=max(110.0, close),
        low=90.0,
        close=close,
        volume=volume,
    )


@pytest.fixture
def store(tmp_path):
    database_path = tmp_path / "data" / "test.sqlite3"
    candle_store = CandleStore(database_path)
    candle_store.initialize()
    return candle_store


def test_initialize_creates_database(store):
    candles = store.get_candles(
        "indodax", "ETH/USDT", "15m"
    )

    assert candles == ()


def test_save_and_read_candle(store):
    candle = make_candle()

    count = store.save_closed_candles(
        [candle],
        now_ms=BASE_TS + 900_000,
    )

    result = store.get_candles(
        "indodax", "ETH/USDT", "15m"
    )

    assert count == 1
    assert len(result) == 1
    assert result[0] == candle


def test_saving_same_candle_does_not_duplicate(store):
    candle = make_candle()

    store.save_closed_candles(
        [candle], now_ms=BASE_TS + 900_000
    )
    store.save_closed_candles(
        [candle], now_ms=BASE_TS + 900_000
    )

    result = store.get_candles(
        "indodax", "ETH/USDT", "15m"
    )

    assert len(result) == 1


def test_existing_candle_can_be_updated(store):
    original = make_candle(close=105.0)
    corrected = make_candle(close=106.0)

    store.save_closed_candles(
        [original], now_ms=BASE_TS + 900_000
    )
    store.save_closed_candles(
        [corrected], now_ms=BASE_TS + 900_000
    )

    result = store.get_candles(
        "indodax", "ETH/USDT", "15m"
    )

    assert len(result) == 1
    assert result[0].close == 106.0


def test_open_candle_is_rejected(store):
    candle = make_candle()

    with pytest.raises(ValueError, match="belum ditutup"):
        store.save_closed_candles(
            [candle],
            now_ms=BASE_TS + 899_999,
        )

    assert store.get_candles(
        "indodax", "ETH/USDT", "15m"
    ) == ()


def test_candles_are_returned_in_chronological_order(store):
    candles = [
        make_candle(timestamp_ms=BASE_TS + 1_800_000),
        make_candle(timestamp_ms=BASE_TS),
        make_candle(timestamp_ms=BASE_TS + 900_000),
    ]

    store.save_closed_candles(
        candles,
        now_ms=BASE_TS + 2_700_000,
    )

    result = store.get_candles(
        "indodax", "ETH/USDT", "15m"
    )

    assert [
        candle.timestamp_ms for candle in result
    ] == [
        BASE_TS,
        BASE_TS + 900_000,
        BASE_TS + 1_800_000,
    ]


def test_limit_returns_most_recent_candles(store):
    candles = [
        make_candle(timestamp_ms=BASE_TS),
        make_candle(timestamp_ms=BASE_TS + 900_000),
        make_candle(timestamp_ms=BASE_TS + 1_800_000),
    ]

    store.save_closed_candles(
        candles,
        now_ms=BASE_TS + 2_700_000,
    )

    result = store.get_candles(
        "indodax", "ETH/USDT", "15m", limit=2
    )

    assert len(result) == 2
    assert result[0].timestamp_ms == BASE_TS + 900_000
    assert result[1].timestamp_ms == BASE_TS + 1_800_000


def test_invalid_limit_is_rejected(store):
    with pytest.raises(ValueError, match="limit minimal 1"):
        store.get_candles(
            "indodax", "ETH/USDT", "15m", limit=0
        )


def test_empty_save_is_safe(store):
    count = store.save_closed_candles(
        [],
        now_ms=BASE_TS,
    )

    assert count == 0
