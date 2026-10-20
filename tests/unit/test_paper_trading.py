import unittest
import pytest
from decimal import Decimal
from app.paper_trading.engine import PaperTradingEngine
from unittest.mock import patch

from app.paper_trading.models import (
    OrderSide,
    OrderStatus,
    PaperConfig,
    PaperPosition,
    PaperTrade,
)


class TestPaperConfig(unittest.TestCase):
    def test_default_config(self):
        config = PaperConfig()

        self.assertEqual(
            config.initial_balance_idr,
            Decimal("1000000"),
        )
        self.assertEqual(config.fee_rate, Decimal("0.002"))

    def test_rejects_non_positive_balance(self):
        with self.assertRaises(ValueError):
            PaperConfig(initial_balance_idr=Decimal("0"))

    def test_rejects_invalid_fee(self):
        with self.assertRaises(ValueError):
            PaperConfig(fee_rate=Decimal("1"))

    def test_rejects_nan_fee(self):
        with self.assertRaises(ValueError):
            PaperConfig(fee_rate=Decimal("NaN"))

    def test_rejects_infinite_initial_balance(self):
        with self.assertRaises(ValueError):
            PaperConfig(initial_balance_idr=Decimal("Infinity"))

    def test_rejects_infinite_fee(self):
        with self.assertRaises(ValueError):
            PaperConfig(fee_rate=Decimal("Infinity"))


class TestPaperPosition(unittest.TestCase):
    def test_valid_position(self):
        position = PaperPosition(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            average_entry_price=Decimal("40000000"),
            entry_fee_idr=Decimal("800"),
        )

        self.assertEqual(position.symbol, "ETH/IDR")
        self.assertEqual(position.quantity, Decimal("0.01"))

    def test_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            PaperPosition(
                symbol="ETH/IDR",
                quantity=Decimal("0"),
                average_entry_price=Decimal("40000000"),
                entry_fee_idr=Decimal("0"),
            )

    
    def test_rejects_non_string_symbol(self):
        with self.assertRaises(ValueError):
            PaperPosition(
                symbol=None,
                quantity=Decimal("0.01"),
                average_entry_price=Decimal("40000000"),
                entry_fee_idr=Decimal("800"),
            )

    def test_rejects_non_decimal_quantity(self):
        with self.assertRaises(ValueError):
            PaperPosition(
                symbol="ETH/IDR",
                quantity=0.01,
                average_entry_price=Decimal("40000000"),
                entry_fee_idr=Decimal("800"),
            )

    def test_rejects_non_decimal_entry_price(self):
        with self.assertRaises(ValueError):
            PaperPosition(
                symbol="ETH/IDR",
                quantity=Decimal("0.01"),
                average_entry_price=40000000,
                entry_fee_idr=Decimal("800"),
            )

    def test_rejects_non_decimal_entry_fee(self):
        with self.assertRaises(ValueError):
            PaperPosition(
                symbol="ETH/IDR",
                quantity=Decimal("0.01"),
                average_entry_price=Decimal("40000000"),
                entry_fee_idr=800,
            )

    def test_rejects_nan_quantity(self):
        with self.assertRaises(ValueError):
            PaperPosition(
                symbol="ETH/IDR",
                quantity=Decimal("NaN"),
                average_entry_price=Decimal("40000000"),
                entry_fee_idr=Decimal("800"),
            )

    def test_rejects_infinite_entry_price(self):
        with self.assertRaises(ValueError):
            PaperPosition(
                symbol="ETH/IDR",
                quantity=Decimal("0.01"),
                average_entry_price=Decimal("Infinity"),
                entry_fee_idr=Decimal("800"),
            )

    def test_rejects_nan_entry_fee(self):
        with self.assertRaises(ValueError):
            PaperPosition(
                symbol="ETH/IDR",
                quantity=Decimal("0.01"),
                average_entry_price=Decimal("40000000"),
                entry_fee_idr=Decimal("NaN"),
            )

class TestPaperTrade(unittest.TestCase):
    def test_valid_trade(self):
        trade = PaperTrade(
            symbol="BTC/IDR",
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
            price=Decimal("1500000000"),
            fee_idr=Decimal("3000"),
            timestamp_ms=1792430400000,
            status=OrderStatus.FILLED,
        )

        self.assertEqual(trade.side, OrderSide.BUY)
        self.assertEqual(trade.status, OrderStatus.FILLED)

    def test_rejects_negative_fee(self):
        with self.assertRaises(ValueError):
            PaperTrade(
                symbol="ETH/IDR",
                side=OrderSide.SELL,
                quantity=Decimal("0.01"),
                price=Decimal("40000000"),
                fee_idr=Decimal("-1"),
                timestamp_ms=1792430400000,
                status=OrderStatus.REJECTED,
            )

    def test_rejected_trade_requires_reason(self):
        with pytest.raises(ValueError, match="alasan penolakan"):
            PaperTrade(
                symbol="ETH/USDT",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                price=Decimal("100"),
                fee_idr=Decimal("0"),
                timestamp_ms=1,
                status=OrderStatus.REJECTED,
            )

    def test_filled_trade_rejects_reason(self):
        with pytest.raises(ValueError, match="alasan penolakan"):
            PaperTrade(
                symbol="ETH/USDT",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                price=Decimal("100"),
                fee_idr=Decimal("0"),
                timestamp_ms=1,
                status=OrderStatus.FILLED,
                reason="Saldo tidak mencukupi.",
            )

    def test_rejects_infinite_quantity(self):
        with self.assertRaises(ValueError):
            PaperTrade(
                symbol="ETH/IDR",
                side=OrderSide.BUY,
                quantity=Decimal("Infinity"),
                price=Decimal("40000000"),
                fee_idr=Decimal("800"),
                timestamp_ms=1792430400000,
                status=OrderStatus.FILLED,
            )

    def test_rejects_nan_price(self):
        with self.assertRaises(ValueError):
            PaperTrade(
                symbol="ETH/IDR",
                side=OrderSide.BUY,
                quantity=Decimal("0.01"),
                price=Decimal("NaN"),
                fee_idr=Decimal("800"),
                timestamp_ms=1792430400000,
                status=OrderStatus.FILLED,
            )

    def test_rejects_infinite_fee(self):
        with self.assertRaises(ValueError):
            PaperTrade(
                symbol="ETH/IDR",
                side=OrderSide.BUY,
                quantity=Decimal("0.01"),
                price=Decimal("40000000"),
                fee_idr=Decimal("Infinity"),
                timestamp_ms=1792430400000,
                status=OrderStatus.FILLED,
            )

class TestPaperTradingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PaperTradingEngine()
        self.timestamp_ms = 1792430400000

    def test_buy_deducts_balance_and_fee(self):
        trade = self.engine.buy(
            "ETH/IDR",
            Decimal("0.01"),
            Decimal("40000000"),
            self.timestamp_ms,
        )

        self.assertEqual(trade.status, OrderStatus.FILLED)
        self.assertEqual(trade.fee_idr, Decimal("800.00000"))
        self.assertEqual(
            self.engine.cash_balance_idr,
            Decimal("599200.00000"),
        )
        self.assertEqual(
            self.engine.positions["ETH/IDR"].quantity,
            Decimal("0.01"),
        )

    def test_sell_calculates_realized_pnl_after_both_fees(self):
        self.engine.buy(
            "ETH/IDR",
            Decimal("0.01"),
            Decimal("40000000"),
            self.timestamp_ms,
        )

        trade = self.engine.sell(
            "ETH/IDR",
            Decimal("0.01"),
            Decimal("41000000"),
            self.timestamp_ms + 1,
        )

        self.assertEqual(trade.status, OrderStatus.FILLED)
        self.assertEqual(trade.fee_idr, Decimal("820.00000"))
        self.assertEqual(
            self.engine.realized_pnl_idr,
            Decimal("8380.00000"),
        )
        self.assertEqual(
            self.engine.cash_balance_idr,
            Decimal("1008380.00000"),
        )
        self.assertNotIn("ETH/IDR", self.engine.positions)


    def test_realized_pnl_reconciles_after_multiple_buys_and_full_sell(self):
        engine = PaperTradingEngine()

        buy_1 = engine.buy(
            "ETH/IDR",
            Decimal("1"),
            Decimal("1000"),
            timestamp_ms=1,
        )
        buy_2 = engine.buy(
            "ETH/IDR",
            Decimal("2"),
            Decimal("2000"),
            timestamp_ms=2,
        )

        sell_trades = [
            engine.sell(
                "ETH/IDR",
                Decimal("1"),
                Decimal("1800"),
                timestamp_ms=timestamp,
            )
            for timestamp in (3, 4, 5)
        ]

        total_buy_cost = (
            Decimal("1") * Decimal("1000")
            + buy_1.fee_idr
            + Decimal("2") * Decimal("2000")
            + buy_2.fee_idr
        )
        total_sell_proceeds = sum(
            (
                trade.quantity * trade.price - trade.fee_idr
                for trade in sell_trades
            ),
            Decimal("0"),
        )

        expected_pnl = total_sell_proceeds - total_buy_cost

        self.assertTrue(
            all(trade.status == OrderStatus.FILLED for trade in sell_trades)
        )
        self.assertNotIn("ETH/IDR", engine.positions)
        self.assertAlmostEqual(
            float(engine.realized_pnl_idr),
            float(expected_pnl),
            places=20,
        )

    def test_buy_rejected_when_balance_is_insufficient(self):
        trade = self.engine.buy(
            "BTC/IDR",
            Decimal("1"),
            Decimal("1500000000"),
            self.timestamp_ms,
        )

        self.assertEqual(trade.status, OrderStatus.REJECTED)
        self.assertEqual(
            self.engine.cash_balance_idr,
            Decimal("1000000"),
        )
        self.assertNotIn("BTC/IDR", self.engine.positions)

    def test_sell_rejected_when_position_does_not_exist(self):
        trade = self.engine.sell(
            "ETH/IDR",
            Decimal("0.01"),
            Decimal("40000000"),
            self.timestamp_ms,
        )

        self.assertEqual(trade.status, OrderStatus.REJECTED)
        self.assertEqual(
            self.engine.cash_balance_idr,
            Decimal("1000000"),
        )

    def test_sell_rejected_when_quantity_exceeds_position(self):
        self.engine.buy(
            "ETH/IDR",
            Decimal("0.01"),
            Decimal("40000000"),
            self.timestamp_ms,
        )

        balance_before = self.engine.cash_balance_idr

        trade = self.engine.sell(
            "ETH/IDR",
            Decimal("0.02"),
            Decimal("41000000"),
            self.timestamp_ms + 1,
        )

        self.assertEqual(trade.status, OrderStatus.REJECTED)
        self.assertEqual(self.engine.cash_balance_idr, balance_before)
        self.assertEqual(
            self.engine.positions["ETH/IDR"].quantity,
            Decimal("0.01"),
        )

    def test_partial_sell_keeps_remaining_position(self):
        self.engine.buy(
            "ETH/IDR",
            Decimal("0.02"),
            Decimal("40000000"),
            self.timestamp_ms,
        )

        trade = self.engine.sell(
            "ETH/IDR",
            Decimal("0.01"),
            Decimal("41000000"),
            self.timestamp_ms + 1,
        )

        self.assertEqual(trade.status, OrderStatus.FILLED)
        self.assertEqual(
            self.engine.positions["ETH/IDR"].quantity,
            Decimal("0.01"),
        )
        self.assertEqual(
            self.engine.positions["ETH/IDR"].entry_fee_idr,
            Decimal("800.00000"),
        )

        
    def test_multiple_buys_calculate_weighted_average_entry(self):
        engine = PaperTradingEngine()
        initial_balance = engine.cash_balance_idr

        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            price=Decimal("40000000"),
            timestamp_ms=1,
        )
        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            price=Decimal("50000000"),
            timestamp_ms=2,
        )

        position = engine.positions["ETH/IDR"]

        self.assertEqual(position.quantity, Decimal("0.02"))
        self.assertEqual(
            position.average_entry_price,
            Decimal("45000000"),
        )
        self.assertEqual(
            position.entry_fee_idr,
            Decimal("1800.00000"),
        )
        self.assertEqual(
            engine.cash_balance_idr,
            initial_balance - Decimal("901800"),
        )


    def test_rejected_buy_does_not_change_balance_or_position(self):
        engine = PaperTradingEngine()
        initial_balance = engine.cash_balance_idr

        trade = engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("1"),
            price=Decimal("2000000"),
            timestamp_ms=1,
        )

        self.assertEqual(trade.status, OrderStatus.REJECTED)
        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertNotIn("ETH/IDR", engine.positions)
        self.assertEqual(len(engine.trades), 1)


    def test_full_sell_closes_position_and_calculates_pnl(self):
        engine = PaperTradingEngine()

        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            price=Decimal("40000000"),
            timestamp_ms=1,
        )
        trade = engine.sell(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            price=Decimal("50000000"),
            timestamp_ms=2,
        )

        self.assertEqual(trade.status, OrderStatus.FILLED)
        self.assertNotIn("ETH/IDR", engine.positions)
        self.assertEqual(
            engine.realized_pnl_idr,
            Decimal("98200"),
        )

    def test_buy_rejects_nan_quantity(self):
        engine = PaperTradingEngine()
        initial_balance = engine.cash_balance_idr

        with self.assertRaises(ValueError):
            engine.buy(
                symbol="ETH/IDR",
                quantity=Decimal("NaN"),
                price=Decimal("40000000"),
                timestamp_ms=1,
            )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertNotIn("ETH/IDR", engine.positions)
        self.assertEqual(len(engine.trades), 0)


    def test_buy_rejects_infinite_price(self):
        engine = PaperTradingEngine()
        initial_balance = engine.cash_balance_idr

        with self.assertRaises(ValueError):
            engine.buy(
                symbol="ETH/IDR",
                quantity=Decimal("0.01"),
                price=Decimal("Infinity"),
                timestamp_ms=1,
            )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertNotIn("ETH/IDR", engine.positions)
        self.assertEqual(len(engine.trades), 0)


    def test_buy_rejects_non_integer_timestamp(self):
        engine = PaperTradingEngine()
        initial_balance = engine.cash_balance_idr

        with self.assertRaises(ValueError):
            engine.buy(
                symbol="ETH/IDR",
                quantity=Decimal("0.01"),
                price=Decimal("40000000"),
                timestamp_ms=1.5,
            )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertNotIn("ETH/IDR", engine.positions)
        self.assertEqual(len(engine.trades), 0)

    
    
    def test_multiple_partial_sells_preserve_remaining_entry_fee(self):
        engine = PaperTradingEngine()

        engine.buy(
            "ETH/IDR",
            Decimal("0.02"),
            Decimal("40000000"),
            timestamp_ms=1,
        )

        initial_position = engine.positions["ETH/IDR"]
        initial_entry_fee = initial_position.entry_fee_idr

        # Penjualan pertama: 0.005 dari 0.02 ETH.
        engine.sell(
            "ETH/IDR",
            Decimal("0.005"),
            Decimal("50000000"),
            timestamp_ms=2,
        )

        position_after_first_sell = engine.positions["ETH/IDR"]

        self.assertEqual(
            position_after_first_sell.quantity,
            Decimal("0.015"),
        )
        self.assertEqual(
            position_after_first_sell.entry_fee_idr,
            initial_entry_fee * Decimal("0.75"),
        )

        # Penjualan kedua: 0.005 ETH lagi.
        engine.sell(
            "ETH/IDR",
            Decimal("0.005"),
            Decimal("50000000"),
            timestamp_ms=3,
        )

        final_position = engine.positions["ETH/IDR"]

        self.assertEqual(final_position.quantity, Decimal("0.010"))
        self.assertEqual(
            final_position.entry_fee_idr,
            initial_entry_fee * Decimal("0.5"),
        )
        self.assertEqual(len(engine.trades), 3)
        self.assertEqual(
            engine.realized_pnl_idr,
            Decimal("98200"),
        )


    def test_entry_fee_is_fully_allocated_after_repeated_partial_sells(self):
        engine = PaperTradingEngine()

        engine.buy(
            "ETH/IDR",
            Decimal("0.02"),
            Decimal("40000000"),
            timestamp_ms=1,
        )

        initial_entry_fee = engine.positions["ETH/IDR"].entry_fee_idr

        for timestamp in (2, 3):
            engine.sell(
                "ETH/IDR",
                Decimal("0.005"),
                Decimal("45000000"),
                timestamp_ms=timestamp,
            )

        remaining_position = engine.positions["ETH/IDR"]

        self.assertEqual(remaining_position.quantity, Decimal("0.010"))
        self.assertEqual(
            remaining_position.entry_fee_idr,
            initial_entry_fee / Decimal("2"),
        )

        engine.sell(
            "ETH/IDR",
            Decimal("0.010"),
            Decimal("45000000"),
            timestamp_ms=4,
        )

        self.assertNotIn("ETH/IDR", engine.positions)
        self.assertEqual(len(engine.trades), 4)
        self.assertEqual(
            engine.realized_pnl_idr,
            Decimal("96600"),
        )
    
    def test_buy_with_extreme_finite_values_does_not_corrupt_state(self):
        engine = PaperTradingEngine()

        initial_balance = engine.cash_balance_idr
        initial_pnl = engine.realized_pnl_idr

        with self.assertRaises(ValueError):
            engine.buy(
                "ETH/IDR",
                Decimal("1E+999999"),
                Decimal("40000000"),
                timestamp_ms=1,
            )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.realized_pnl_idr, initial_pnl)
        self.assertNotIn("ETH/IDR", engine.positions)
        self.assertEqual(len(engine.trades), 0)


    def test_rejects_non_decimal_initial_balance(self):
        with self.assertRaises(ValueError):
            PaperConfig(initial_balance_idr=1000000)

    def test_rejects_non_decimal_fee_rate(self):
        with self.assertRaises(ValueError):
            PaperConfig(fee_rate=0.002)

    def test_buy_recording_failure_does_not_change_state(self):
        engine = PaperTradingEngine()

        initial_balance = engine.cash_balance_idr
        initial_positions = engine.positions.copy()
        initial_trade_count = len(engine.trades)

        with patch.object(
            engine,
            "_record_trade",
            side_effect=RuntimeError("Simulated recording failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Simulated recording failure",
            ):
                engine.buy(
                    symbol="ETH/IDR",
                    quantity=Decimal("0.01"),
                    price=Decimal("40000000"),
                    timestamp_ms=1,
                )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(len(engine.trades), initial_trade_count)

    
    def test_sell_with_extreme_finite_values_does_not_corrupt_state(self):
        engine = PaperTradingEngine()

        engine.buy(
            "ETH/IDR",
            Decimal("10"),
            Decimal("1"),
            timestamp_ms=1,
        )

        initial_balance = engine.cash_balance_idr
        initial_positions = engine.positions.copy()
        initial_pnl = engine.realized_pnl_idr
        initial_trade_count = len(engine.trades)

        with self.assertRaises(ValueError):
            engine.sell(
                "ETH/IDR",
                Decimal("10"),
                Decimal("1E+999999"),
                timestamp_ms=2,
            )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(engine.realized_pnl_idr, initial_pnl)
        self.assertEqual(len(engine.trades), initial_trade_count)
    
    def test_sell_recording_failure_does_not_change_state(self):
        engine = PaperTradingEngine()

        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            price=Decimal("40000000"),
            timestamp_ms=1,
        )

        initial_balance = engine.cash_balance_idr
        initial_positions = engine.positions.copy()
        initial_realized_pnl = engine.realized_pnl_idr
        initial_trade_count = len(engine.trades)

        with patch.object(
            engine,
            "_record_trade",
            side_effect=RuntimeError("Simulated recording failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Simulated recording failure",
            ):
                engine.sell(
                    symbol="ETH/IDR",
                    quantity=Decimal("0.005"),
                    price=Decimal("41000000"),
                    timestamp_ms=2,
                )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(engine.realized_pnl_idr, initial_realized_pnl)
        self.assertEqual(len(engine.trades), initial_trade_count)

    
    def test_sell_position_update_failure_does_not_change_state(self):
        engine = PaperTradingEngine()

        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            price=Decimal("40000000"),
            timestamp_ms=1,
        )

        initial_balance = engine.cash_balance_idr
        initial_positions = engine.positions.copy()
        initial_realized_pnl = engine.realized_pnl_idr
        initial_trade_count = len(engine.trades)

        with patch(
            "app.paper_trading.engine.PaperPosition",
            side_effect=RuntimeError("Simulated position update failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Simulated position update failure",
            ):
                engine.sell(
                    symbol="ETH/IDR",
                    quantity=Decimal("0.005"),
                    price=Decimal("41000000"),
                    timestamp_ms=2,
                )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(engine.realized_pnl_idr, initial_realized_pnl)
        self.assertEqual(len(engine.trades), initial_trade_count)

    
    
    def test_buy_with_extreme_values_on_existing_position_does_not_corrupt_state(self):
        engine = PaperTradingEngine()

        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            price=Decimal("40000000"),
            timestamp_ms=1,
        )

        engine.cash_balance_idr = Decimal("1E+999999")
        initial_trade_count = len(engine.trades)

        trade = engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("1E+300000"),
            price=Decimal("1E+300000"),
            timestamp_ms=2,
        )

        self.assertEqual(trade.status, OrderStatus.FILLED)
        self.assertTrue(engine.cash_balance_idr.is_finite())
        self.assertTrue(engine.positions["ETH/IDR"].quantity.is_finite())
        self.assertTrue(engine.positions["ETH/IDR"].average_entry_price.is_finite())
        self.assertTrue(engine.positions["ETH/IDR"].entry_fee_idr.is_finite())
        self.assertEqual(len(engine.trades), initial_trade_count + 1)



    def test_buy_rejects_invalid_internal_balance_without_changing_state(self):
        engine = PaperTradingEngine()
        initial_positions = engine.positions.copy()
        initial_trade_count = len(engine.trades)

        engine.cash_balance_idr = Decimal("NaN")

        with pytest.raises(ValueError):
            engine.buy(
                symbol="ETH/IDR",
                quantity=Decimal("0.01"),
                price=Decimal("40000000"),
                timestamp_ms=1,
            )

        self.assertTrue(engine.cash_balance_idr.is_nan())
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(len(engine.trades), initial_trade_count)

    
    def test_sell_rejects_invalid_internal_balance_without_changing_state(self):
        engine = PaperTradingEngine()
        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("1"),
            price=Decimal("1000"),
            timestamp_ms=1,
        )

        initial_positions = engine.positions.copy()
        initial_trade_count = len(engine.trades)
        initial_realized_pnl = engine.realized_pnl_idr

        engine.cash_balance_idr = Decimal("NaN")

        with pytest.raises(ValueError):
            engine.sell(
                symbol="ETH/IDR",
                quantity=Decimal("0.5"),
                price=Decimal("1200"),
                timestamp_ms=2,
            )

        self.assertTrue(engine.cash_balance_idr.is_nan())
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(len(engine.trades), initial_trade_count)
        self.assertEqual(engine.realized_pnl_idr, initial_realized_pnl)

    
    def test_sell_rejects_invalid_internal_realized_pnl_without_changing_state(self):
        engine = PaperTradingEngine()
        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("1"),
            price=Decimal("1000"),
            timestamp_ms=1,
        )

        initial_balance = engine.cash_balance_idr
        initial_positions = engine.positions.copy()
        initial_trade_count = len(engine.trades)

        engine.realized_pnl_idr = Decimal("NaN")

        with pytest.raises(ValueError):
            engine.sell(
                symbol="ETH/IDR",
                quantity=Decimal("0.5"),
                price=Decimal("1200"),
                timestamp_ms=2,
            )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(len(engine.trades), initial_trade_count)
        self.assertTrue(engine.realized_pnl_idr.is_nan())
        
    def test_buy_balance_calculation_failure_does_not_change_state(self):
        engine = PaperTradingEngine()
        initial_balance = engine.cash_balance_idr
        initial_positions = engine.positions.copy()
        initial_trade_count = len(engine.trades)

        with patch.object(
            engine,
            "_validate_finite_results",
            side_effect=[
                None,  # Validasi hasil biaya pembelian.
                None,  # Validasi saldo awal.
                ValueError("Simulated balance validation failure."),
            ],
        ):
            with pytest.raises(
                ValueError,
                match="Simulated balance validation failure",
            ):
                engine.buy(
                    symbol="ETH/IDR",
                    quantity=Decimal("0.01"),
                    price=Decimal("40000000"),
                    timestamp_ms=1,
                )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(len(engine.trades), initial_trade_count)

    def test_buy_decimal_overflow_does_not_change_state(self):
        engine = PaperTradingEngine()

        initial_balance = engine.cash_balance_idr
        initial_positions = engine.positions.copy()
        initial_trade_count = len(engine.trades)

        with self.assertRaises(ValueError):
            engine.buy(
                symbol="ETH/IDR",
                quantity=Decimal("1E+999999"),
                price=Decimal("1E+999999"),
                timestamp_ms=1,
            )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(len(engine.trades), initial_trade_count)


    def test_sell_validation_failure_does_not_change_state(self):
        engine = PaperTradingEngine()

        engine.buy(
            symbol="ETH/IDR",
            quantity=Decimal("0.01"),
            price=Decimal("40000000"),
            timestamp_ms=1,
        )

        initial_balance = engine.cash_balance_idr
        initial_positions = engine.positions.copy()
        initial_realized_pnl = engine.realized_pnl_idr
        initial_trade_count = len(engine.trades)

        with patch.object(
            engine,
            "_validate_finite_results",
            side_effect=[
                None,
                ValueError("Simulated non-finite calculation result."),
            ],
        ):
            with self.assertRaises(ValueError):
                engine.sell(
                    symbol="ETH/IDR",
                    quantity=Decimal("0.01"),
                    price=Decimal("50000000"),
                    timestamp_ms=2,
                )

        self.assertEqual(engine.cash_balance_idr, initial_balance)
        self.assertEqual(engine.positions, initial_positions)
        self.assertEqual(engine.realized_pnl_idr, initial_realized_pnl)
        self.assertEqual(len(engine.trades), initial_trade_count)


if __name__ == "__main__":
    unittest.main()