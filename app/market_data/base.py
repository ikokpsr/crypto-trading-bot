from typing import Protocol

from app.domain.candle import Candle


class MarketDataProvider(Protocol):
    def fetch_closed_candles(
        self,
        limit: int = 100,
        now_ms: int | None = None,
    ) -> tuple[Candle, ...]:
        ...