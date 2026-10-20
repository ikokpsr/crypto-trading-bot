
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from urllib.request import Request, urlopen

import ccxt


def get_usd_idr_rate() -> Decimal:
    """Mengambil kurs USD/IDR dari sumber kurs publik."""
    request = Request(
        "https://open.er-api.com/v6/latest/USD",
        headers={"User-Agent": "CryptoTradingBot/1.0"},
    )

    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("result") != "success":
            raise ValueError("Kurs USD/IDR tidak tersedia.")

        rate = Decimal(str(data["rates"]["IDR"]))

    except (OSError, TimeoutError, ValueError, KeyError, TypeError,
            InvalidOperation, json.JSONDecodeError):
        raise ValueError(
            "Gagal mengambil kurs USD/IDR yang valid."
        ) from None

    if not rate.is_finite() or rate <= 0:
        raise ValueError("Kurs USD/IDR tidak valid.")

    return rate


def _valid_price(value) -> Decimal | None:
    """Mengubah harga menjadi Decimal positif yang valid."""
    if value is None:
        return None

    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

    if not price.is_finite() or price <= 0:
        return None

    return price


def get_asset_idr_prices(
    exchange,
    assets: set[str],
) -> dict[str, Decimal]:
    """
    Mengambil harga IDR untuk aset yang memiliki pasar aktif.

    Prioritas:
    1. Pasangan langsung ASSET/IDR.
    2. Pasangan ASSET/USDT dikalikan harga USDT/IDR.

    Aset tanpa sumber harga yang valid tidak dimasukkan ke hasil.
    """
    markets = exchange.load_markets()
    direct_markets: dict[str, str] = {}
    usdt_markets: dict[str, str] = {}

    for symbol, market in markets.items():
        if not market.get("active", True):
            continue

        base = market.get("base")
        quote = market.get("quote")

        if not isinstance(base, str) or not isinstance(quote, str):
            continue

        base = base.upper()
        quote = quote.upper()

        if quote == "IDR":
            direct_markets[base] = symbol
        elif quote == "USDT":
            usdt_markets[base] = symbol

    prices: dict[str, Decimal] = {"IDR": Decimal("1")}

    def fetch_price(symbol: str) -> Decimal | None:
        try:
            ticker = exchange.fetch_ticker(symbol)
            return _valid_price(ticker.get("last"))
        except (ccxt.BaseError, ValueError, TypeError, KeyError):
            return None

    # Ambil harga langsung IDR terlebih dahulu.
    for asset in {item.upper() for item in assets}:
        if asset == "IDR":
            continue

        symbol = direct_markets.get(asset)
        if symbol is None:
            continue

        price = fetch_price(symbol)
        if price is not None:
            prices[asset] = price

    # Cari kurs USDT/IDR hanya jika ada aset yang membutuhkan konversi.
    needs_usdt_conversion = any(
        asset not in prices and asset in usdt_markets
        for asset in {item.upper() for item in assets}
    )

    usdt_idr = prices.get("USDT")

    if needs_usdt_conversion and usdt_idr is None:
        usdt_symbol = direct_markets.get("USDT")
        if usdt_symbol is not None:
            usdt_idr = fetch_price(usdt_symbol)

            if usdt_idr is not None:
                prices["USDT"] = usdt_idr

    # Konversi aset berpasangan USDT menjadi estimasi harga IDR.
    if usdt_idr is not None:
        for asset in {item.upper() for item in assets}:
            if asset in prices:
                continue

            symbol = usdt_markets.get(asset)
            if symbol is None:
                continue

            usdt_price = fetch_price(symbol)
            if usdt_price is None:
                continue

            idr_price = _valid_price(usdt_price * usdt_idr)
            if idr_price is not None:
                prices[asset] = idr_price

    return prices
