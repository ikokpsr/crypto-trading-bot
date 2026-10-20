
from decimal import Decimal
from typing import Any

import ccxt

from app.config import load_settings
from app.scanner.market_scanner import (
    MarketCandidate,
    build_market_candidates,
)


class IndodaxScanner:
    """Read-only scanner untuk market spot IDR Indodax."""

    def __init__(self, exchange: Any | None = None) -> None:
        self.exchange = (
            exchange
            if exchange is not None
            else ccxt.indodax({"enableRateLimit": True})
        )
        self._owns_exchange = exchange is None
        self._markets: dict[str, dict[str, Any]] | None = None
        self.settings = load_settings()

    def load_eligible_markets(self) -> dict[str, dict[str, Any]]:
        markets = self.exchange.load_markets()

        eligible = {
            symbol: market
            for symbol, market in markets.items()
            if isinstance(market, dict)
            and market.get("active") is True
            and market.get("spot") is True
            and isinstance(market.get("base"), str)
            and market["base"].strip()
            and market.get("quote") == "IDR"
        }

        self._markets = eligible
        return eligible

    def scan_once(self) -> list[MarketCandidate]:
        if self._markets is None:
            self.load_eligible_markets()

        if not self._markets:
            return []

        if not self.exchange.has.get("fetchTickers"):
            raise RuntimeError(
                "Exchange tidak mendukung pengambilan ticker massal."
            )

        tickers = self.exchange.fetch_tickers()

        return build_market_candidates(
            markets=self._markets,
            tickers=tickers,
            quote_currency="IDR",
            max_spread_pct=Decimal(
                str(self.settings.scanner_max_spread_pct)
            ),
            min_quote_volume=Decimal(
                str(self.settings.scanner_min_quote_volume_idr)
            ),
        )

    def close(self) -> None:
        if self._owns_exchange:
            self.exchange.close()
