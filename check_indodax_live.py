
from datetime import datetime, timezone

import ccxt


def utc(timestamp_ms):
    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def main():
    exchange = ccxt.indodax({"enableRateLimit": True})

    try:
        exchange.load_markets()

        symbol = "ETH/USDT"
        market = exchange.market(symbol)

        print("=== MARKET ===")
        print(f"Symbol CCXT : {symbol}")
        print(f"Symbol API  : {market['id']}")

        ticker = exchange.fetch_ticker(symbol)

        print("\n=== TICKER TERKINI ===")
        print(f"Last  : {ticker.get('last')}")
        print(f"Bid   : {ticker.get('bid')}")
        print(f"Ask   : {ticker.get('ask')}")
        print(f"Volume 24 jam: {ticker.get('baseVolume')} ETH")

        candles = exchange.fetch_ohlcv(
            symbol,
            timeframe="15m",
            limit=10,
        )

        print("\n=== 10 CANDLE TERAKHIR DARI CCXT ===")

        for timestamp, open_, high, low, close, volume in candles:
            print(
                f"{utc(timestamp)} | "
                f"O={open_} H={high} L={low} "
                f"C={close} V={volume}"
            )

        print("\n=== RINGKASAN ===")
        positive_volume = sum(
            1 for candle in candles if candle[5] > 0
        )
        print(f"Candle diperiksa : {len(candles)}")
        print(f"Volume positif   : {positive_volume}")
        print(f"Volume nol       : {len(candles) - positive_volume}")

    finally:
        exchange.close()


if __name__ == "__main__":
    main()
