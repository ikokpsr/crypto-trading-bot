
from datetime import datetime, timezone

from app.market_data.ccxt_provider import IndodaxMarketData


def main() -> None:
    provider = IndodaxMarketData(
        symbol="ETH/USDT",
        timeframe="15m",
    )

    try:
        print("Menghubungi Indodax...")
        provider.load_markets()

        # Gunakan waktu server exchange agar pemeriksaan
        # candle tertutup tidak hanya bergantung pada jam PC.
        now_ms = provider.exchange.fetch_time()

        candles = provider.fetch_closed_candles(
            limit=5,
            now_ms=now_ms,
        )

        print(f"Exchange: indodax")
        print(f"Symbol: {provider.symbol}")
        print(f"Timeframe: {provider.timeframe}")
        print(f"Candle tertutup ditemukan: {len(candles)}")

        if not candles:
            print(
                "Belum ada candle tertutup yang dikembalikan. "
                "Periksa respons exchange dan waktu server."
            )
            return

        for candle in candles:
            open_time = candle.open_time.isoformat()
            print(
                f"{open_time} | "
                f"O={candle.open} "
                f"H={candle.high} "
                f"L={candle.low} "
                f"C={candle.close} "
                f"V={candle.volume}"
            )

        newest = candles[-1]
        newest_close_time = datetime.fromtimestamp(
            newest.close_time_ms / 1000,
            tz=timezone.utc,
        )

        print(f"Candle terakhir dibuka: {newest.open_time.isoformat()}")
        print(f"Candle terakhir ditutup: {newest_close_time.isoformat()}")
        print("Uji market data selesai. Tidak ada order dikirim.")

    except Exception as exc:
        print(f"Uji market data gagal: {type(exc).__name__}: {exc}")
        raise

    finally:
        provider.close()


if __name__ == "__main__":
    main()
