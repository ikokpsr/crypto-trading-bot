
import ccxt

CANDIDATES = ["ETH/IDR", "BTC/IDR"]


def main():
    exchange = ccxt.indodax({"enableRateLimit": True})

    try:
        markets = exchange.load_markets()

        print("=== ATURAN MARKET INDODAX ===")
        print("Mode: inspeksi publik, tanpa order")

        for symbol in CANDIDATES:
            print(f"\n{'=' * 45}")
            print(f"Market: {symbol}")

            market = markets.get(symbol)

            if market is None:
                print("Market tidak ditemukan.")
                continue

            limits = market.get("limits") or {}
            precision = market.get("precision") or {}

            amount_limits = limits.get("amount") or {}
            price_limits = limits.get("price") or {}
            cost_limits = limits.get("cost") or {}

            print(f"Active          : {market.get('active')}")
            print(f"Base currency   : {market.get('base')}")
            print(f"Quote currency  : {market.get('quote')}")
            print(f"Maker fee       : {market.get('maker')}")
            print(f"Taker fee       : {market.get('taker')}")

            print(f"Amount precision: {precision.get('amount')}")
            print(f"Price precision : {precision.get('price')}")

            print(f"Min amount      : {amount_limits.get('min')}")
            print(f"Max amount      : {amount_limits.get('max')}")
            print(f"Min price       : {price_limits.get('min')}")
            print(f"Max price       : {price_limits.get('max')}")
            print(f"Min cost        : {cost_limits.get('min')}")
            print(f"Max cost        : {cost_limits.get('max')}")

            print(f"CCXT precisionMode: {exchange.precisionMode}")
            print(f"CCXT precisionMode DECIMAL_PLACES: {ccxt.DECIMAL_PLACES}")
            print(f"CCXT precisionMode TICK_SIZE: {ccxt.TICK_SIZE}")
            print(f"Market percentage: {market.get('percentage')}")
            print(f"Raw fee metadata: {market.get('info', {}).get('trade_fee_percent')}")
            print(f"CCXT taker fee: {market.get('taker')}")
            print(f"CCXT maker fee: {market.get('maker')}")
            print(f"Raw amount precision: {market.get('precision', {}).get('amount')}")
            print(f"Raw price precision: {market.get('precision', {}).get('price')}")

            print("\nCatatan: nilai None berarti metadata tersebut")
            print("tidak tersedia dari respons CCXT ini;")
            print("bukan berarti tidak ada batasan di exchange.")
            

    finally:
        exchange.close()


if __name__ == "__main__":
    main()
