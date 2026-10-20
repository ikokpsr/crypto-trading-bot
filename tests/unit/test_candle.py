
import pytest

from app.domain.candle import Candle


def make_candle(**overrides):
    data = {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "timeframe": "15m",
        "timestamp_ms": 1_797_840_000_000,
        "open": 100.0,
        "high": 110.0,
        "low": 95.0,
        "close": 105.0,
        "volume": 12.0,
    }
    data.update(overrides)
    return Candle(**data)


def test_valid_candle_can_be_created():
    candle = make_candle()

    assert candle.symbol == "BTC/USDT"
    assert candle.timeframe == "15m"


def test_candle_rejects_invalid_timeframe():
    with pytest.raises(ValueError, match="Timeframe tidak didukung"):
        make_candle(timeframe="1h")


def test_candle_rejects_inconsistent_high():
    with pytest.raises(ValueError, match="High tidak konsisten"):
        make_candle(high=104.0)


def test_candle_rejects_negative_volume():
    with pytest.raises(ValueError, match="Volume tidak boleh negatif"):
        make_candle(volume=-1.0)


def test_candle_rejects_nan_price():
    with pytest.raises(ValueError, match="finite"):
        make_candle(close=float("nan"))


def test_candle_is_not_closed_before_interval_ends():
    candle = make_candle()

    assert candle.is_closed(candle.timestamp_ms + 899_999) is False


def test_candle_is_closed_at_interval_end():
    candle = make_candle()

    assert candle.is_closed(candle.timestamp_ms + 900_000) is True


def test_candle_open_time_is_utc():
    candle = make_candle()

    assert candle.open_time.tzinfo is not None
    assert candle.open_time.utcoffset().total_seconds() == 0


@pytest.mark.parametrize("timestamp", [123.5, True, "123"])
def test_candle_rejects_non_integer_timestamp(timestamp):
    with pytest.raises(
        ValueError,
        match="Timestamp harus berupa bilangan bulat",
    ):
        make_candle(timestamp_ms=timestamp)