
from datetime import datetime, timezone

from app.config import load_settings
from app.market_data.ccxt_provider import IndodaxMarketData
from app.market_data.quality import find_data_quality_warnings
from app.storage.database import CandleStore


def main() -> None:
    settings = load_settings()

    if settings.exchange_id != "indodax":
        raise ValueError(
            "Skrip ini khusus untuk EXCHANGE_ID=indodax."
        )

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    provider = IndodaxMarketData(
        symbol="ETH/USDT",
        timeframe=settings.timeframe,
    )

    try:
        print("Memulai sinkronisasi market data...")
        print(f"Exchange: {settings.exchange_id}")
        print("Symbol: ETH/USDT")
        print(f"Timeframe: {settings.timeframe}")
        print(f"Database: {settings.database_path}")

        candles = provider.fetch_closed_candles(
            limit=100,
            now_ms=now_ms,
        )

        print(f"\nCandle tertutup ditemukan: {len(candles)}")

        warnings = find_data_quality_warnings(
            candles=candles,
            now_ms=now_ms,
        )

        store = CandleStore(settings.database_path)
        store.initialize()

        processed = store.save_closed_candles(
            candles=candles,
            now_ms=now_ms,
        )

        print(f"Candle diproses untuk penyimpanan: {processed}")

        if candles:
            latest = candles[-1]
            print("\nCandle terbaru:")
            print(
                "Waktu buka UTC: "
                f"{latest.open_time.isoformat()}"
            )
            print(
                "Waktu tutup UTC: "
                f"{datetime.fromtimestamp(latest.close_time_ms / 1000, tz=timezone.utc).isoformat()}"
            )
            print(f"Close: {latest.close}")
            print(f"Volume: {latest.volume}")

        if warnings:
            print("\nPERINGATAN KUALITAS DATA:")
            for warning in warnings:
                print(f"- {warning}")
        else:
            print("\nPemeriksaan kualitas data: tidak ada peringatan.")

        saved_candles = store.get_candles(
            exchange=settings.exchange_id,
            symbol="ETH/USDT",
            timeframe=settings.timeframe,
            limit=100,
        )

        print(
            "\nJumlah candle dalam database untuk "
            f"100 data terbaru: {len(saved_candles)}"
        )

        print("Sinkronisasi selesai. Tidak ada order dikirim.")

    finally:
        provider.close()


if __name__ == "__main__":
    main()
