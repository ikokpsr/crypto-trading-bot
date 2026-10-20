
import unittest
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from app.scanner.execution_estimator import (
    DEFAULT_MIN_ORDER_COST,
    TARGET_NET_PROFIT_PCT,
    ExecutionEstimate,
)
from app.scanner.profitability_scanner import ProfitabilityScanner
from app.storage.market_snapshot_store import MarketSnapshotStore


def make_candidate(
    symbol="BTC/IDR",
    spread_pct=Decimal("0.1"),
    quote_volume=Decimal("20000000"),
):
    candidate = Mock()
    candidate.symbol = symbol
    candidate.spread_pct = spread_pct
    candidate.quote_volume = quote_volume
    return candidate


def make_market(
    amount_step="0.00000001",
    min_amount="0",
    min_cost=None,
):
    return {
        "precision": {
            "amount": float(amount_step),
        },
        "limits": {
            "amount": {
                "min": (
                    None
                    if min_amount is None
                    else float(min_amount)
                ),
            },
            "cost": {
                "min": (
                    None
                    if min_cost is None
                    else float(min_cost)
                ),
            },
        },
    }


def make_order_book(
    ask="100",
    bid="99",
    ask_amount="10000",
    bid_amount="10000",
):
    return {
        "asks": [[float(ask), float(ask_amount)]],
        "bids": [[float(bid), float(bid_amount)]],
    }


def make_estimate(net_profit, net_profit_pct):
    return ExecutionEstimate(
        buy_cost=Decimal("100000"),
        buy_fee=Decimal("200"),
        base_amount=Decimal("1000"),
        sell_proceeds=Decimal("101000"),
        sell_fee=Decimal("400"),
        net_profit=Decimal(str(net_profit)),
        net_profit_pct=Decimal(str(net_profit_pct)),
    )


class TestProfitabilityScanner(unittest.TestCase):
    def setUp(self):
        self.scanner = Mock()

        self.scanner._markets = {
            "BTC/IDR": make_market(),
            "ETH/IDR": make_market(),
        }

        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
            make_candidate("ETH/IDR"),
        ]

        self.scanner.exchange.fetch_order_book.side_effect = [
            make_order_book(ask="100", bid="99"),
            make_order_book(ask="100", bid="99"),
        ]

        self.evaluator = ProfitabilityScanner(
            scanner=self.scanner,
            max_order_books=20,
            target_net_profit_pct=TARGET_NET_PROFIT_PCT,
        )

    def test_returns_only_candidates_above_net_profit_target(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
            make_candidate("ETH/IDR"),
        ]

        with patch(
            "app.scanner.profitability_scanner.estimate_round_trip",
            side_effect=[
                make_estimate("600", "0.6"),
                make_estimate("-619.83", "-0.6198"),
            ],
        ):
            results = self.evaluator.scan_once()

        self.assertEqual(
            [result.symbol for result in results],
            ["BTC/IDR"],
        )
        self.assertGreaterEqual(
            results[0].net_profit_pct,
            TARGET_NET_PROFIT_PCT,
        )
        self.assertGreaterEqual(
            results[0].net_profit,
            Decimal("500"),
        )

    def test_rejects_insufficient_sell_depth(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
        ]
        self.scanner._markets = {
            "BTC/IDR": make_market(),
        }
        self.scanner.exchange.fetch_order_book.side_effect = None
        self.scanner.exchange.fetch_order_book.return_value = (
            make_order_book(bid_amount="0.000001")
        )

        results = self.evaluator.scan_once()

        self.assertEqual(results, [])

    def test_limits_number_of_order_book_requests(self):
        self.scanner.scan_once.return_value = [
            make_candidate(f"COIN{i}/IDR")
            for i in range(5)
        ]
        self.scanner._markets = {
            f"COIN{i}/IDR": make_market()
            for i in range(5)
        }
        self.scanner.exchange.fetch_order_book.side_effect = None
        self.scanner.exchange.fetch_order_book.return_value = (
            make_order_book(ask="100", bid="99")
        )

        evaluator = ProfitabilityScanner(
            scanner=self.scanner,
            max_order_books=2,
        )

        evaluator.scan_once()

        self.assertEqual(
            self.scanner.exchange.fetch_order_book.call_count,
            2,
        )

    def test_skips_market_when_order_book_request_fails(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
            make_candidate("ETH/IDR"),
        ]
        self.scanner.exchange.fetch_order_book.side_effect = [
            RuntimeError("Simulated API failure"),
            make_order_book(ask="100", bid="99"),
        ]

        results = self.evaluator.scan_once()

        self.assertEqual(results, [])

    def test_rejects_invalid_order_book_limit(self):
        with self.assertRaises(ValueError):
            ProfitabilityScanner(
                scanner=self.scanner,
                max_order_books=0,
            )

    def test_rejects_negative_profit_target(self):
        with self.assertRaises(ValueError):
            ProfitabilityScanner(
                scanner=self.scanner,
                target_net_profit_pct=Decimal("-0.1"),
            )

    def test_saves_snapshots_for_positive_and_negative_profit(self):
        with TemporaryDirectory() as temp_dir:
            store = MarketSnapshotStore(
                f"{temp_dir}/snapshots.sqlite3"
            )
            self.scanner.scan_once.return_value = [
                make_candidate("BTC/IDR"),
                make_candidate("ETH/IDR"),
            ]
            self.scanner.exchange.fetch_order_book.side_effect = [
                make_order_book(ask="100", bid="99"),
                make_order_book(ask="100", bid="99"),
            ]

            evaluator = ProfitabilityScanner(
                scanner=self.scanner,
                snapshot_store=store,
            )

            with patch(
                "app.scanner.profitability_scanner.estimate_round_trip",
                side_effect=[
                    make_estimate("600", "0.6"),
                    make_estimate("-619.83", "-0.6198"),
                ],
            ):
                results = evaluator.scan_once()

            snapshots = store.get_snapshots(limit=10)

            self.assertEqual(
                [item.symbol for item in results],
                ["BTC/IDR"],
            )
            self.assertEqual(len(snapshots), 2)
            self.assertEqual(
                {item["symbol"] for item in snapshots},
                {"BTC/IDR", "ETH/IDR"},
            )

            btc_snapshot = next(
                item for item in snapshots
                if item["symbol"] == "BTC/IDR"
            )
            eth_snapshot = next(
                item for item in snapshots
                if item["symbol"] == "ETH/IDR"
            )

            self.assertEqual(
                btc_snapshot["net_profit_pct"],
                Decimal("0.6"),
            )
            self.assertEqual(
                eth_snapshot["net_profit_pct"],
                Decimal("-0.6198"),
            )
            self.assertEqual(
                evaluator.last_diagnostics.snapshots_saved,
                2,
            )
            self.assertEqual(
                evaluator.last_diagnostics.snapshot_save_failures,
                0,
            )

    def test_does_not_save_snapshot_when_estimate_is_invalid(self):
        with TemporaryDirectory() as temp_dir:
            store = MarketSnapshotStore(
                f"{temp_dir}/snapshots.sqlite3"
            )
            self.scanner.scan_once.return_value = [
                make_candidate("BTC/IDR"),
            ]
            self.scanner.exchange.fetch_order_book.side_effect = None
            self.scanner.exchange.fetch_order_book.return_value = (
                make_order_book(bid_amount="0.000001")
            )

            evaluator = ProfitabilityScanner(
                scanner=self.scanner,
                snapshot_store=store,
            )

            results = evaluator.scan_once()

            self.assertEqual(results, [])
            self.assertEqual(store.get_snapshots(), ())
            self.assertEqual(
                evaluator.last_diagnostics.snapshots_saved,
                0,
            )

    def test_uses_default_minimum_cost_when_metadata_is_missing(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
        ]
        self.scanner._markets = {
            "BTC/IDR": make_market(min_cost=None),
        }
        self.scanner.exchange.fetch_order_book.side_effect = None
        self.scanner.exchange.fetch_order_book.return_value = (
            make_order_book()
        )

        with patch(
            "app.scanner.profitability_scanner.estimate_round_trip",
            return_value=make_estimate("600", "0.6"),
        ) as estimate_mock:
            self.evaluator.scan_once()

        self.assertEqual(
            estimate_mock.call_args.kwargs["min_cost"],
            DEFAULT_MIN_ORDER_COST,
        )

    def test_rejects_market_when_minimum_amount_is_missing(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
        ]
        self.scanner._markets = {
            "BTC/IDR": make_market(min_amount=None),
        }

        with patch(
            "app.scanner.profitability_scanner.estimate_round_trip",
        ) as estimate_mock:
            results = self.evaluator.scan_once()

        self.assertEqual(results, [])
        estimate_mock.assert_not_called()
        self.assertEqual(
            self.evaluator.last_diagnostics.invalid_market_metadata,
            1,
        )

    def test_rejects_negative_minimum_cost(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
        ]
        self.scanner._markets = {
            "BTC/IDR": make_market(min_cost="-1"),
        }

        with patch(
            "app.scanner.profitability_scanner.estimate_round_trip",
        ) as estimate_mock:
            results = self.evaluator.scan_once()

        self.assertEqual(results, [])
        estimate_mock.assert_not_called()
        self.assertEqual(
            self.evaluator.last_diagnostics.invalid_market_metadata,
            1,
        )


    def test_rejects_non_mapping_precision_metadata(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
        ]
        self.scanner._markets = {
            "BTC/IDR": {
                "precision": [],
                "limits": make_market()["limits"],
            },
        }

        with patch(
            "app.scanner.profitability_scanner.estimate_round_trip",
        ) as estimate_mock:
            results = self.evaluator.scan_once()

        self.assertEqual(results, [])
        estimate_mock.assert_not_called()
        self.assertEqual(
            self.evaluator.last_diagnostics.invalid_market_metadata,
            1,
        )

    def test_rejects_non_mapping_limits_metadata(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
        ]
        self.scanner._markets = {
            "BTC/IDR": {
                "precision": make_market()["precision"],
                "limits": [],
            },
        }

        with patch(
            "app.scanner.profitability_scanner.estimate_round_trip",
        ) as estimate_mock:
            results = self.evaluator.scan_once()

        self.assertEqual(results, [])
        estimate_mock.assert_not_called()
        self.assertEqual(
            self.evaluator.last_diagnostics.invalid_market_metadata,
            1,
        )

    def test_crossed_order_book_does_not_stop_scan(self):
        self.scanner.scan_once.return_value = [
            make_candidate("BTC/IDR"),
            make_candidate("ETH/IDR"),
        ]
        self.scanner.exchange.fetch_order_book.side_effect = [
            make_order_book(ask="100", bid="101"),
            make_order_book(ask="100", bid="99"),
        ]

        with TemporaryDirectory() as temp_dir:
            store = MarketSnapshotStore(
                f"{temp_dir}/snapshots.sqlite3"
            )
            evaluator = ProfitabilityScanner(
                scanner=self.scanner,
                snapshot_store=store,
            )

            results = evaluator.scan_once()
            snapshots = store.get_snapshots()

        self.assertEqual(
            self.scanner.exchange.fetch_order_book.call_count,
            2,
        )
        self.assertEqual(
            evaluator.last_diagnostics.invalid_order_books,
            1,
        )
        self.assertEqual(
            evaluator.last_diagnostics.snapshots_saved,
            1,
        )
        self.assertEqual(
            [item["symbol"] for item in snapshots],
            ["ETH/IDR"],
        )
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
