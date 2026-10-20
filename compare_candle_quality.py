
from datetime import datetime, timezone

import ccxt

CANDIDATES = ["ETH/USDT", "ETH/IDR", "BTC/IDR"]
TIMEFRAME = "15m"
CANDLE_LIMIT = 100
INTERVAL_MS = 15 * 60 * 1000


def main():
    exchange = ccxt.indodax({"enableRateLimit": True})

    try:
        markets = exchange.load_markets()
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        print("=== PERBANDINGAN KUALITAS CANDLE ===")
        print(f"Timeframe: {TIMEFRAME}")
        print(f"Batas candle: {CANDLE_LIMIT}")
        print("Mode: baca data publik, tanpa order")

        for symbol in CANDIDATES:
            print(f"\n{'=' * 55}")
            print(f"Market: {symbol}")

            market = markets.get(symbol)
            if market is None:
                print("DILEWATI: market tidak ditemukan.")
                continue

            if market.get("active") is False:
                print("DILEWATI: market tidak aktif.")
                continue

            try:
                rows = exchange.fetch_ohlcv(
                    symbol,
                    timeframe=TIMEFRAME,
                    limit=CANDLE_LIMIT,
                )
            except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
                print(f"Gagal mengambil candle: {type(exc).__name__}: {exc}")
                continue

            # Hanya gunakan candle yang sudah ditutup.
            candles = [
                row for row in rows
                if row[0] + INTERVAL_MS <= now_ms
            ]

            candles.sort(key=lambda row: row[0])

            if not candles:
                print("Tidak ada candle tertutup.")
                continue

            total = len(candles)
            zero_volume = sum(row[5] == 0 for row in candles)
            flat_ohlc = sum(
                row[1] == row[2] == row[3] == row[4]
                for row in candles
            )

            gaps = []
            invalid_intervals = 0

            for previous, current in zip(candles, candles[1:]):
                delta = current[0] - previous[0]

                if delta > INTERVAL_MS:
                    gaps.append((delta // INTERVAL_MS) - 1)
                elif delta < INTERVAL_MS:
                    invalid_intervals += 1

            missing_estimate = sum(gaps)

            print(f"Candle tertutup : {total}")
            print(
                f"Volume nol      : {zero_volume} "
                f"({zero_volume / total * 100:.1f}%)"
            )
            print(
                f"OHLC datar      : {flat_ohlc} "
                f"({flat_ohlc / total * 100:.1f}%)"
            )
            print(f"Celah waktu     : {len(gaps)}")
            print(f"Estimasi candle hilang: {missing_estimate}")
            print(f"Interval tidak valid  : {invalid_intervals}")

            latest = candles[-1]
            latest_open = datetime.fromtimestamp(
                latest[0] / 1000, tz=timezone.utc
            )
            latest_close = latest_open.timestamp() + INTERVAL_MS / 1000
            latest_close_dt = datetime.fromtimestamp(
                latest_close, tz=timezone.utc
            )

            print(f"Candle terakhir dibuka : {latest_open.isoformat()}")
            print(f"Candle terakhir ditutup: {latest_close_dt.isoformat()}")
            print(f"Close terakhir         : {latest[4]}")
            print(f"Volume terakhir        : {latest[5]}")

            print("5 candle tertutup terbaru:")
            for row in candles[-5:]:
                timestamp = datetime.fromtimestamp(
                    row[0] / 1000, tz=timezone.utc
                )
                print(
                    f"  {timestamp.isoformat()} | "
                    f"O={row[1]} H={row[2]} L={row[3]} "
                    f"C={row[4]} V={row[5]}"
                )

    finally:
        exchange.close()


if __name__ == "__main__":
    main()
