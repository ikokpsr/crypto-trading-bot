
from decimal import Decimal
from unittest.mock import Mock

import ccxt

from app.account_valuation import get_asset_idr_prices


def make_exchange(markets, ticker_prices):
    exchange = Mock()
    exchange.load_markets.return_value = markets

    def fetch_ticker(symbol):
        if symbol not in ticker_prices:
            raise ccxt.ExchangeError(f"Ticker tidak tersedia: {symbol}")

        return {"last": ticker_prices[symbol]}

    exchange.fetch_ticker.side_effect = fetch_ticker
    return exchange


def test_direct_idr_price():
    exchange = make_exchange(
        {
            "BCH/IDR": {
                "base": "BCH",
                "quote": "IDR",
                "active": True,
            },
        },
        {"BCH/IDR": 5_000_000},
    )

    prices = get_asset_idr_prices(exchange, {"BCH"})

    assert prices["BCH"] == Decimal("5000000")
    assert prices["IDR"] == Decimal("1")


def test_usdt_conversion():
    exchange = make_exchange(
        {
            "USDT/IDR": {
                "base": "USDT",
                "quote": "IDR",
                "active": True,
            },
            "XEC/USDT": {
                "base": "XEC",
                "quote": "USDT",
                "active": True,
            },
        },
        {
            "USDT/IDR": 17921,
            "XEC/USDT": "0.000006",
        },
    )

    prices = get_asset_idr_prices(exchange, {"XEC"})

    assert prices["USDT"] == Decimal("17921")
    assert prices["XEC"] == Decimal("0.107526")


def test_inactive_market_is_ignored():
    exchange = make_exchange(
        {
            "BSV/IDR": {
                "base": "BSV",
                "quote": "IDR",
                "active": False,
            },
        },
        {"BSV/IDR": 100_000},
    )

    prices = get_asset_idr_prices(exchange, {"BSV"})

    assert "BSV" not in prices
    exchange.fetch_ticker.assert_not_called()


def test_missing_market_does_not_create_fake_price():
    exchange = make_exchange({}, {})

    prices = get_asset_idr_prices(exchange, {"BCD", "BTG"})

    assert "BCD" not in prices
    assert "BTG" not in prices


def test_invalid_price_is_ignored():
    exchange = make_exchange(
        {
            "BCH/IDR": {
                "base": "BCH",
                "quote": "IDR",
                "active": True,
            },
        },
        {"BCH/IDR": "NaN"},
    )

    prices = get_asset_idr_prices(exchange, {"BCH"})

    assert "BCH" not in prices


def test_ticker_failure_does_not_stop_other_assets():
    exchange = make_exchange(
        {
            "BCH/IDR": {
                "base": "BCH",
                "quote": "IDR",
                "active": True,
            },
            "XLM/IDR": {
                "base": "XLM",
                "quote": "IDR",
                "active": True,
            },
        },
        {"XLM/IDR": 2500},
    )

    prices = get_asset_idr_prices(exchange, {"BCH", "XLM"})

    assert "BCH" not in prices
    assert prices["XLM"] == Decimal("2500")
