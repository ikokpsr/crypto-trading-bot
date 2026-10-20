
from datetime import datetime, timezone

import ccxt

from app.domain.candle import Candle


class IndodaxMarketData:
    def __init__(
        self,
        symbol: str = "ETH/USDT",
        timeframe: str = "15m",
        exchange=None,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = exchange or ccxt.indodax(
            {"enableRateLimit": True}
        )
        self._owns_exchange = exchange is None
        self._markets_loaded = False

    def load_markets(self) -> None:
        if self._markets_loaded:
            return

        markets = self.exchange.load_markets()

        if not self.exchange.has.get("fetchOHLCV"):
            raise RuntimeError(
                "Exchange tidak mendukung fetchOHLCV."
            )

        if self.timeframe not in (
            self.exchange.timeframes or {}
        ):
            raise ValueError(
                f"Timeframe {self.timeframe} tidak didukung."
            )

        market = markets.get(self.symbol)

        if market is None:
            raise ValueError(
                f"Market {self.symbol} tidak ditemukan "
                "di Indodax melalui CCXT."
            )

        if market.get("active") is False:
            raise ValueError(
                f"Market {self.symbol} sedang tidak aktif."
            )

        self._markets_loaded = True

    def fetch_closed_candles(
        self,
        limit: int = 100,
        now_ms: int | None = None,
    ) -> tuple[Candle, ...]:
        if limit < 1:
            raise ValueError("limit minimal 1.")

        self.load_markets()

        rows = self.exchange.fetch_ohlcv(
            self.symbol,
            timeframe=self.timeframe,
            limit=limit,
        )

        if now_ms is None:
            now_ms = int(
                datetime.now(timezone.utc).timestamp() * 1000
            )

        candles_by_timestamp: dict[int, Candle] = {}

        for row in rows:
            if len(row) < 6:
                raise ValueError("Data OHLCV tidak lengkap.")

            timestamp, open_, high, low, close, volume = row[:6]

            if isinstance(timestamp, bool) or not isinstance(timestamp, int):
                raise ValueError(
                    "Timestamp OHLCV harus berupa bilangan bulat."
                )

            if any(
                value is None
                for value in (
                    timestamp,
                    open_,
                    high,
                    low,
                    close,
                    volume,
                )
            ):
                raise ValueError(
                    "Data OHLCV mengandung nilai kosong."
                )

            candle = Candle(
                exchange="indodax",
                symbol=self.symbol,
                timeframe=self.timeframe,
                timestamp_ms=timestamp,
                open=float(open_),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=float(volume),
            )

            # Jangan biarkan candle yang masih terbentuk
            # masuk ke strategi.
            if candle.is_closed(now_ms):
                candles_by_timestamp[candle.timestamp_ms] = candle

        return tuple(
            candles_by_timestamp[timestamp]
            for timestamp in sorted(candles_by_timestamp)
        )

    def close(self) -> None:
        if self._owns_exchange:
            self.exchange.close()
