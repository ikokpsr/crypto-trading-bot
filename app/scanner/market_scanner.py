
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


@dataclass(frozen=True)
class MarketCandidate:
    symbol: str
    base: str
    quote: str
    bid: Decimal
    ask: Decimal
    last: Decimal | None
    quote_volume: Decimal | None

    @property
    def spread_pct(self) -> Decimal:
        midpoint = (self.bid + self.ask) / Decimal("2")
        return (self.ask - self.bid) / midpoint * Decimal("100")


def _positive_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

    if not result.is_finite() or result <= 0:
        return None

    return result


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

    if not result.is_finite() or result < 0:
        return None

    return result


def build_market_candidates(
    markets: Mapping[str, Mapping[str, Any]],
    tickers: Mapping[str, Mapping[str, Any]],
    *,
    quote_currency: str | None = None,
    max_spread_pct: Decimal | None = None,
    min_quote_volume: Decimal | None = None,
) -> list[MarketCandidate]:
    """Bangun kandidat market dan terapkan filter opsional."""
    if max_spread_pct is not None:
        if (
            not isinstance(max_spread_pct, Decimal)
            or not max_spread_pct.is_finite()
            or max_spread_pct <= 0
        ):
            raise ValueError("max_spread_pct harus finite dan positif.")

    if min_quote_volume is not None:
        if (
            not isinstance(min_quote_volume, Decimal)
            or not min_quote_volume.is_finite()
            or min_quote_volume < 0
        ):
            raise ValueError(
                "min_quote_volume harus finite dan tidak negatif."
            )

    candidates: list[MarketCandidate] = []

    for symbol, market in markets.items():
        if market.get("active") is not True:
            continue

        if market.get("spot") is not True:
            continue

        base = market.get("base")
        quote = market.get("quote")

        if (
            not isinstance(base, str)
            or not base.strip()
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            continue

        if quote_currency is not None and quote != quote_currency:
            continue

        ticker = tickers.get(symbol)
        if not isinstance(ticker, Mapping):
            continue

        bid = _positive_decimal(ticker.get("bid"))
        ask = _positive_decimal(ticker.get("ask"))

        if bid is None or ask is None or ask < bid:
            continue

        last = _optional_decimal(ticker.get("last"))
        quote_volume = _optional_decimal(ticker.get("quoteVolume"))

        candidate = MarketCandidate(
            symbol=symbol,
            base=base,
            quote=quote,
            bid=bid,
            ask=ask,
            last=last,
            quote_volume=quote_volume,
        )

        if (
            max_spread_pct is not None
            and candidate.spread_pct > max_spread_pct
        ):
            continue

        if min_quote_volume is not None:
            if (
                quote_volume is None
                or quote_volume < min_quote_volume
            ):
                continue

        candidates.append(candidate)

    return sorted(candidates, key=lambda candidate: candidate.symbol)
