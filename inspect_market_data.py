
from datetime import datetime, timezone

from app.config import load_settings
from app.domain.candle import TIMEFRAME_SECONDS
from app.storage.database import CandleStore


def format_utc(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def main() -> None:
    settings = load_settings()
    symbol = "ETH/USDT"
    timeframe = settings.timeframe

    store = CandleStore(settings.database_path)
    store.initialize()

    candles = store.get_candles(
        exchange=settings.exchange_id,
        symbol=symbol,
        timeframe=timeframe,
        limit=1000,
    )

    print("=== DIAGNOSTIK MARKET DATA ===")
    print(f"Exchange : {settings.exchange_id}")
    print(f"Symbol   : {symbol}")
    print(f"Timeframe: {timeframe}")
    print(f"Database : {settings.database_path}")

    if not candles:
        print("\nBelum ada candle tersimpan.")
        return

    interval_ms = TIMEFRAME_SECONDS[timeframe] * 1000

    total = len(candles)
    zero_volume = sum(c.volume == 0 for c in candles)
    flat_ohlc = sum(
        c.open == c.high == c.low == c.close
        for c in candles
    )

    gaps = []
    invalid_intervals = []

    for previous, current in zip(candles, candles[1:]):
        delta = current.timestamp_ms - previous.timestamp_ms

        if delta > interval_ms:
            missing = delta // interval_ms - 1
            gaps.append(missing)
        elif delta < interval_ms:
            invalid_intervals.append(delta)

    print(f"\nJumlah candle       : {total}")
    print(f"Volume nol          : {zero_volume} ({zero_volume / total:.1%})")
    print(f"OHLC datar          : {flat_ohlc} ({flat_ohlc / total:.1%})")
    print(f"Jumlah celah waktu  : {len(gaps)}")
    print(f"Estimasi candle hilang: {sum(gaps)}")
    print(f"Interval tidak valid: {len(invalid_intervals)}")

    print("\n=== RENTANG DATA ===")
    print(f"Candle tertua : {format_utc(candles[0].timestamp_ms)}")
    print(f"Candle terbaru: {format_utc(candles[-1].timestamp_ms)}")

    elapsed_ms = (
        candles[-1].timestamp_ms - candles[0].timestamp_ms
    )
    expected_intervals = elapsed_ms // interval_ms + 1

    print(f"Interval yang seharusnya tercakup: {expected_intervals}")
    print(f"Interval yang tersimpan          : {total}")

    print("\n=== 10 CANDLE TERBARU ===")
    for candle in candles[-10:]:
        print(
            f"{format_utc(candle.timestamp_ms)} | "
            f"O={candle.open} H={candle.high} "
            f"L={candle.low} C={candle.close} "
            f"V={candle.volume}"
        )

    print("\n=== PENILAIAN AWAL ===")

    if zero_volume / total >= 0.5:
        print("- Mayoritas candle tidak memiliki volume.")
    elif zero_volume > 0:
        print("- Ada candle tanpa volume.")

    if flat_ohlc / total >= 0.5:
        print("- Mayoritas candle memiliki OHLC datar.")
    elif flat_ohlc > 0:
        print("- Ada candle dengan OHLC datar.")

    if gaps:
        print("- Ada celah timestamp yang perlu diperiksa.")

    if invalid_intervals:
        print("- Ada interval timestamp yang tidak sesuai timeframe.")

    if not zero_volume and not flat_ohlc and not gaps and not invalid_intervals:
        print("- Tidak ditemukan anomali dasar pada metrik yang diperiksa.")

    print(
        "\nCatatan: laporan ini memeriksa konsistensi dasar, "
        "bukan menjamin data layak untuk trading."
    )


if __name__ == "__main__":
    main()
