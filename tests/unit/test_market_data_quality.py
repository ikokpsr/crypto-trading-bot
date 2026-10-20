
from app.domain.candle import Candle
from app.market_data.quality import find_data_quality_warnings


BASE_TS = 1_797_840_000_000


def make_candle(timestamp, volume=10.0, price=100.0):
    return Candle(
        exchange="indodax",
        symbol="ETH/USDT",
        timeframe="15m",
        timestamp_ms=timestamp,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=volume,
    )


def test_warns_when_latest_volume_is_zero():
    candles = (make_candle(BASE_TS, volume=0),)

    warnings = find_data_quality_warnings(
        candles,
        now_ms=BASE_TS + 900_000,
    )

    assert any("volume candle terakhir nol" in w for w in warnings)


def test_warns_when_data_is_stale():
    candles = (make_candle(BASE_TS),)

    warnings = find_data_quality_warnings(
        candles,
        now_ms=BASE_TS + 2_400_000,
    )

    assert any("basi" in w for w in warnings)


def test_warns_when_candle_gap_exists():
    candles = (
        make_candle(BASE_TS),
        make_candle(BASE_TS + 1_800_000),
    )

    warnings = find_data_quality_warnings(
        candles,
        now_ms=BASE_TS + 2_700_000,
    )

    assert any("celah data" in w for w in warnings)


def test_clean_candle_has_no_warning():
    candles = (make_candle(BASE_TS, price=100.0),)

    warnings = find_data_quality_warnings(
        candles,
        now_ms=BASE_TS + 900_000,
    )

    assert warnings == []
