import unittest
from unittest.mock import Mock

from app.scanner.indodax_scanner import IndodaxScanner


def make_market(base="BTC", quote="IDR", active=True, spot=True):
    return {
        "active": active,
        "spot": spot,
        "base": base,
        "quote": quote,
    }


def make_ticker(bid=100, ask=100.1, last=100, quote_volume=20_000_000):
    return {
        "bid": bid,
        "ask": ask,
        "last": last,
        "quoteVolume": quote_volume,
    }



class TestIndodaxScanner(unittest.TestCase):
    def setUp(self):
        self.exchange = Mock()
        self.exchange.has = {"fetchTickers": True}
        self.exchange.load_markets.return_value = {
            "BTC/IDR": make_market(),
            "ETH/IDR": make_market(base="ETH"),
            "OLD/IDR": make_market(base="OLD", active=False),
            "FUTURE/IDR": make_market(base="FUTURE", spot=False),
        }
        self.exchange.fetch_tickers.return_value = {
            "BTC/IDR": make_ticker(),
            "ETH/IDR": make_ticker(bid=200, ask=200.2),
            "OLD/IDR": make_ticker(),
            "FUTURE/IDR": make_ticker(),
        }
        self.scanner = IndodaxScanner(exchange=self.exchange)

    def test_loads_only_active_spot_markets(self):
        markets = self.scanner.load_eligible_markets()

        self.assertEqual(set(markets), {"BTC/IDR", "ETH/IDR"})
        self.exchange.load_markets.assert_called_once()

    def test_scan_returns_candidates_for_active_spot_markets(self):
        candidates = self.scanner.scan_once()

        self.assertEqual(
            [candidate.symbol for candidate in candidates],
            ["BTC/IDR", "ETH/IDR"],
        )
        self.exchange.load_markets.assert_called_once()
        self.exchange.fetch_tickers.assert_called_once()

    def test_reuses_loaded_markets_on_repeated_scans(self):
        self.scanner.scan_once()
        self.scanner.scan_once()

        self.exchange.load_markets.assert_called_once()
        self.assertEqual(self.exchange.fetch_tickers.call_count, 2)

    def test_does_not_fetch_tickers_when_no_eligible_markets(self):
        self.exchange.load_markets.return_value = {
            "OLD/IDR": make_market(base="OLD", active=False),
        }

        candidates = self.scanner.scan_once()

        self.assertEqual(candidates, [])
        self.exchange.fetch_tickers.assert_not_called()

    def test_raises_if_bulk_tickers_are_not_supported(self):
        self.exchange.has = {"fetchTickers": False}

        with self.assertRaisesRegex(
            RuntimeError,
            "tidak mendukung pengambilan ticker massal",
        ):
            self.scanner.scan_once()

        self.exchange.fetch_tickers.assert_not_called()

    def test_missing_ticker_excludes_market(self):
        self.exchange.fetch_tickers.return_value = {
            "BTC/IDR": make_ticker(),
        }

        candidates = self.scanner.scan_once()

        self.assertEqual(
            [candidate.symbol for candidate in candidates],
            ["BTC/IDR"],
        )

    
    def test_rejects_market_with_spread_above_configured_limit(self):
        self.exchange.fetch_tickers.return_value = {
            "BTC/IDR": make_ticker(bid=100, ask=101),
            "ETH/IDR": make_ticker(bid=200, ask=200.2),
        }

        candidates = self.scanner.scan_once()

        self.assertEqual(
            [candidate.symbol for candidate in candidates],
            ["ETH/IDR"],
        )

    def test_rejects_market_with_low_quote_volume(self):
        self.exchange.fetch_tickers.return_value = {
            "BTC/IDR": make_ticker(quote_volume=9_999_999),
            "ETH/IDR": make_ticker(quote_volume=10_000_000),
        }

        candidates = self.scanner.scan_once()

        self.assertEqual(
            [candidate.symbol for candidate in candidates],
            ["ETH/IDR"],
        )


    def test_injected_exchange_is_not_closed_by_scanner(self):
        self.scanner.close()

        self.exchange.close.assert_not_called()

    def test_owned_exchange_is_closed(self):
        scanner = IndodaxScanner.__new__(IndodaxScanner)
        scanner.exchange = Mock()
        scanner._owns_exchange = True
        scanner._markets = None

        scanner.close()

        scanner.exchange.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()