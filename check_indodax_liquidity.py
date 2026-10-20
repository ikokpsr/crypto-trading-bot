
import ccxt


def main():
    exchange = ccxt.indodax({"enableRateLimit": True})

    try:
        symbol = "ETH/USDT"
        exchange.load_markets()

        order_book = exchange.fetch_order_book(symbol, limit=5)
        trades = exchange.fetch_trades(symbol, limit=20)

        bids = order_book["bids"]
        asks = order_book["asks"]

        print("=== ORDER BOOK ===")

        if not bids or not asks:
            print("Order book tidak memiliki bid atau ask.")
        else:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2
            spread_pct = (best_ask - best_bid) / mid_price * 100

            print(f"Best bid: {best_bid}")
            print(f"Best ask: {best_ask}")
            print(f"Spread  : {spread_pct:.4f}%")

            print("\nTop 5 bids:")
            for price, amount in bids:
                print(f"Price={price} Amount={amount}")

            print("\nTop 5 asks:")
            for price, amount in asks:
                print(f"Price={price} Amount={amount}")

        print("\n=== TRANSAKSI TERAKHIR ===")
        print(f"Jumlah transaksi diterima: {len(trades)}")

        for trade in trades[-10:]:
            print(
                f"Side={trade.get('side')} "
                f"Price={trade.get('price')} "
                f"Amount={trade.get('amount')} "
                f"Timestamp={trade.get('datetime')}"
            )

    finally:
        exchange.close()


if __name__ == "__main__":
    main()
