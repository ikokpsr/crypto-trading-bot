import unittest
from decimal import Decimal

from app.scanner.market_scanner import build_market_candidates


def make_market(
    *,
    active=True,
    spot=True,
    base="BTC",
    quote="IDR",
):
    return {
        "active": active,
        "spot": spot,
        "base": base,
        "quote": quote,
    }


def make_ticker(*, bid=100, ask=101, last=100, quote_volume=1_000_000):
    return {
        "bid": bid,
        "ask": ask,
        "last": last,
        "quoteVolume": quote_volume,
    }


class TestBuildMarketCandidates(unittest.TestCase):
    def test_accepts_active_spot_market_with_valid_ticker(self):
        candidates = build_market_candidates(
            {"BTC/IDR": make_market()},
            {"BTC/IDR": make_ticker()},
        )

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.symbol, "BTC/IDR")
        self.assertEqual(candidate.base, "BTC")
        self.assertEqual(candidate.quote, "IDR")
        self.assertEqual(candidate.bid, Decimal("100"))
        self.assertEqual(candidate.ask, Decimal("101"))
        self.assertEqual(candidate.last, Decimal("100"))
        self.assertEqual(candidate.quote_volume, Decimal("1000000"))

    def test_rejects_inactive_market(self):
        candidates = build_market_candidates(
            {"BTC/IDR": make_market(active=False)},
            {"BTC/IDR": make_ticker()},
        )

        self.assertEqual(candidates, [])

    def test_rejects_unknown_active_status(self):
        candidates = build_market_candidates(
            {"BTC/IDR": make_market(active=None)},
            {"BTC/IDR": make_ticker()},
        )

        self.assertEqual(candidates, [])

    def test_rejects_non_spot_market(self):
        candidates = build_market_candidates(
            {"BTC/IDR": make_market(spot=False)},
            {"BTC/IDR": make_ticker()},
        )

        self.assertEqual(candidates, [])

    def test_rejects_market_with_missing_ticker(self):
        candidates = build_market_candidates(
            {"BTC/IDR": make_market()},
            {},
        )

        self.assertEqual(candidates, [])

    def test_rejects_missing_or_invalid_bid_ask(self):
        invalid_tickers = [
            {"bid": None, "ask": 101},
            {"bid": 100, "ask": None},
            {"bid": 0, "ask": 101},
            {"bid": -1, "ask": 101},
            {"bid": "invalid", "ask": 101},
            {"bid": 102, "ask": 101},
            {"bid": float("nan"), "ask": 101},
            {"bid": float("inf"), "ask": 101},
            {"bid": True, "ask": 101},
        ]

        for ticker in invalid_tickers:
            with self.subTest(ticker=ticker):
                candidates = build_market_candidates(
                    {"BTC/IDR": make_market()},
                    {"BTC/IDR": ticker},
                )
                self.assertEqual(candidates, [])

    def test_allows_missing_optional_last_and_volume(self):
        candidates = build_market_candidates(
            {"BTC/IDR": make_market()},
            {"BTC/IDR": {"bid": 100, "ask": 101}},
        )

        self.assertEqual(len(candidates), 1)
        self.assertIsNone(candidates[0].last)
        self.assertIsNone(candidates[0].quote_volume)

    def test_rejects_invalid_market_metadata(self):
        invalid_markets = [
            make_market(base=None),
            make_market(base=""),
            make_market(quote=None),
            make_market(quote=" "),
        ]

        for market in invalid_markets:
            with self.subTest(market=market):
                candidates = build_market_candidates(
                    {"BTC/IDR": market},
                    {"BTC/IDR": make_ticker()},
                )
                self.assertEqual(candidates, [])

    def test_candidates_are_sorted_by_symbol(self):
        markets = {
            "ETH/IDR": make_market(base="ETH"),
            "BTC/IDR": make_market(base="BTC"),
        }
        tickers = {
            "ETH/IDR": make_ticker(bid=200, ask=201),
            "BTC/IDR": make_ticker(bid=100, ask=101),
        }

        candidates = build_market_candidates(markets, tickers)

        self.assertEqual(
            [candidate.symbol for candidate in candidates],
            ["BTC/IDR", "ETH/IDR"],
        )

    def test_spread_percentage_uses_midpoint(self):
        candidates = build_market_candidates(
            {"BTC/IDR": make_market()},
            {"BTC/IDR": make_ticker(bid=100, ask=102)},
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0].spread_pct,
            Decimal("2") / Decimal("101") * Decimal("100"),
        )



    def test_filters_by_quote_currency(self):
        markets = {
            "BTC/IDR": make_market(base="BTC", quote="IDR"),
            "BTC/USDT": make_market(base="BTC", quote="USDT"),
        }
        tickers = {
            "BTC/IDR": make_ticker(),
            "BTC/USDT": make_ticker(),
        }

        candidates = build_market_candidates(
            markets,
            tickers,
            quote_currency="IDR",
        )

        self.assertEqual(
            [candidate.symbol for candidate in candidates],
            ["BTC/IDR"],
        )

    def test_rejects_spread_above_limit(self):
        candidates = build_market_candidates(
            {"BTC/IDR": make_market()},
            {"BTC/IDR": make_ticker(bid=100, ask=102)},
            max_spread_pct=Decimal("1"),
        )

        self.assertEqual(candidates, [])

    def test_rejects_low_or_missing_quote_volume(self):
        markets = {
            "BTC/IDR": make_market(base="BTC"),
            "ETH/IDR": make_market(base="ETH"),
            "SOL/IDR": make_market(base="SOL"),
        }
        tickers = {
            "BTC/IDR": make_ticker(quote_volume=9_999_999),
            "ETH/IDR": make_ticker(quote_volume=10_000_000),
            "SOL/IDR": {"bid": 100, "ask": 101},
        }

        candidates = build_market_candidates(
            markets,
            tickers,
            min_quote_volume=Decimal("10000000"),
        )

        self.assertEqual(
            [candidate.symbol for candidate in candidates],
            ["ETH/IDR"],
        )


if __name__ == "__main__":
    unittest.main()