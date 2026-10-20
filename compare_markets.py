
import ccxt


CANDIDATES = ["ETH/USDT", "ETH/IDR", "BTC/IDR"]
ORDER_BOOK_LIMIT = 20
TRADE_LIMIT = 100


def main():
    exchange = ccxt.indodax({"enableRateLimit": True})

    try:
        markets = exchange.load_markets()

        print("=== PERBANDINGAN LIKUIDITAS INDODAX ===")
        print("Hanya membaca data publik; tidak ada order.")

        for symbol in CANDIDATES:
            print(f"\n{'=' * 55}")
            print(f"Market: {symbol}")

            market = markets.get(symbol)
            if market is None:
                print("DILEWATI: market tidak tersedia di CCXT.")
                continue

            if market.get("active") is False:
                print("DILEWATI: market ditandai tidak aktif.")
                continue

            try:
                ticker = exchange.fetch_ticker(symbol)
                book = exchange.fetch_order_book(
                    symbol,
                    limit=ORDER_BOOK_LIMIT,
                )
                trades = exchange.fetch_trades(
                    symbol,
                    limit=TRADE_LIMIT,
                )
            except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
                print(f"Gagal mengambil data: {type(exc).__name__}: {exc}")
                continue

            bid = book["bids"][0] if book["bids"] else None
            ask = book["asks"][0] if book["asks"] else None

            print(f"Last price     : {ticker.get('last')}")
            print(f"Base volume 24h: {ticker.get('baseVolume')}")
            print(f"Quote volume 24h: {ticker.get('quoteVolume')}")
            print(f"Trade samples  : {len(trades)}")

            if bid and ask and bid[0] > 0 and ask[0] >= bid[0]:
                mid = (bid[0] + ask[0]) / 2
                spread_pct = (ask[0] - bid[0]) / mid * 100

                print(f"Best bid       : {bid[0]}")
                print(f"Best ask       : {ask[0]}")
                print(f"Spread         : {spread_pct:.4f}%")

                # Kedalaman dalam rentang 0,5% dari mid-price.
                bid_depth = sum(
                    price * amount
                    for price, amount, *_ in book["bids"]
                    if price >= mid * (1 - 0.005)
                )
                ask_depth = sum(
                    price * amount
                    for price, amount, *_ in book["asks"]
                    if price <= mid * (1 + 0.005)
                )

                quote = market.get("quote", "")
                print(
                    f"Bid depth ±0,5%: {bid_depth:.8f} {quote}"
                )
                print(
                    f"Ask depth ±0,5%: {ask_depth:.8f} {quote}"
                )
            else:
                print("Spread/depth: order book tidak lengkap.")

            if trades:
                timestamps = [
                    trade["timestamp"]
                    for trade in trades
                    if trade.get("timestamp") is not None
                ]
                if timestamps:
                    span_minutes = (
                        max(timestamps) - min(timestamps)
                    ) / 60_000
                    print(
                        "Rentang sampel transaksi: "
                        f"{span_minutes:.2f} menit"
                    )

                print("Transaksi terbaru:")
                for trade in trades[-5:]:
                    print(
                        f"  {trade.get('datetime')} | "
                        f"{trade.get('side')} | "
                        f"price={trade.get('price')} | "
                        f"amount={trade.get('amount')}"
                    )
            else:
                print("Tidak ada transaksi pada sampel yang diterima.")

    finally:
        exchange.close()


if __name__ == "__main__":
    main()
