
import pytest

from app.market_data.ccxt_provider import IndodaxMarketData


BASE_TS = 1_797_840_000_000


class FakeExchange:
    has = {"fetchOHLCV": True}
    timeframes = {"15m": "15"}

    def __init__(self, markets=None, rows=None):
        self.markets = (
            markets
            if markets is not None
            else {
                "ETH/USDT": {
                    "symbol": "ETH/USDT",
                    "active": True,
                }
            }
        )
        self.rows = rows or []
        self.fetch_calls = 0
        self.closed = False

    def load_markets(self):
        return self.markets

    def fetch_ohlcv(self, symbol, timeframe, limit):
        self.fetch_calls += 1
        assert symbol == "ETH/USDT"
        assert timeframe == "15m"
        return self.rows[:limit]

    def close(self):
        self.closed = True


def row(timestamp):
    return [
        timestamp,
        100.0,
        110.0,
        90.0,
        105.0,
        12.0,
    ]


def test_returns_only_closed_candles():
    exchange = FakeExchange(
        rows=[
            row(BASE_TS),
            row(BASE_TS + 900_000),
        ]
    )
    provider = IndodaxMarketData(exchange=exchange)

    candles = provider.fetch_closed_candles(
        now_ms=BASE_TS + 900_000
    )

    assert len(candles) == 1
    assert candles[0].timestamp_ms == BASE_TS


def test_returns_candles_in_timestamp_order():
    exchange = FakeExchange(
        rows=[
            row(BASE_TS + 900_000),
            row(BASE_TS),
        ]
    )
    provider = IndodaxMarketData(exchange=exchange)

    candles = provider.fetch_closed_candles(
        now_ms=BASE_TS + 1_800_000
    )

    assert [
        candle.timestamp_ms for candle in candles
    ] == [BASE_TS, BASE_TS + 900_000]


def test_duplicate_timestamps_are_deduplicated():
    exchange = FakeExchange(
        rows=[
            row(BASE_TS),
            row(BASE_TS),
        ]
    )
    provider = IndodaxMarketData(exchange=exchange)

    candles = provider.fetch_closed_candles(
        now_ms=BASE_TS + 900_000
    )

    assert len(candles) == 1


def test_missing_market_is_rejected():
    exchange = FakeExchange(markets={})
    provider = IndodaxMarketData(exchange=exchange)

    with pytest.raises(ValueError, match="tidak ditemukan"):
        provider.fetch_closed_candles(
            now_ms=BASE_TS + 900_000
        )

    assert exchange.fetch_calls == 0


def test_invalid_ohlcv_is_rejected():
    exchange = FakeExchange(rows=[[BASE_TS, 100.0]])
    provider = IndodaxMarketData(exchange=exchange)

    with pytest.raises(ValueError, match="tidak lengkap"):
        provider.fetch_closed_candles(
            now_ms=BASE_TS + 900_000
        )


def test_non_positive_limit_is_rejected():
    exchange = FakeExchange()
    provider = IndodaxMarketData(exchange=exchange)

    with pytest.raises(ValueError, match="minimal 1"):
        provider.fetch_closed_candles(limit=0)

    assert exchange.fetch_calls == 0

@pytest.mark.parametrize("timestamp", [BASE_TS + 0.5, True, str(BASE_TS)])
def test_rejects_non_integer_ohlcv_timestamp(timestamp):
    exchange = FakeExchange(rows=[row(timestamp)])
    provider = IndodaxMarketData(exchange=exchange)

    with pytest.raises(
        ValueError,
        match="Timestamp OHLCV harus berupa bilangan bulat",
    ):
        provider.fetch_closed_candles(
            now_ms=BASE_TS + 900_000
        )