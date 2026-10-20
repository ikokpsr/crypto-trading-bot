
from app.domain.candle import Candle


def find_data_quality_warnings(
    candles: tuple[Candle, ...],
    now_ms: int,
    max_age_ms: int = 20 * 60 * 1000,
) -> list[str]:
    if not candles:
        return ["Tidak ada candle tersedia."]

    warnings: list[str] = []
    ordered = sorted(candles, key=lambda candle: candle.timestamp_ms)

    if len({c.timestamp_ms for c in ordered}) != len(ordered):
        warnings.append("Ada timestamp candle duplikat.")

    latest = ordered[-1]

    if not latest.is_closed(now_ms):
        warnings.append("Candle terbaru belum ditutup.")

    age_ms = now_ms - latest.close_time_ms

    if age_ms > max_age_ms:
        warnings.append(
            f"Data candle terakhir basi: terlambat {age_ms // 1000} detik."
        )

    if latest.volume == 0:
        warnings.append("volume candle terakhir nol")

    interval_ms = 15 * 60 * 1000

    for previous, current in zip(ordered, ordered[1:]):
        delta = current.timestamp_ms - previous.timestamp_ms

        if delta < interval_ms:
            warnings.append("Ada jarak timestamp yang tidak valid.")
            break

        if delta > interval_ms:
            missing = delta // interval_ms - 1
            warnings.append(
                f"Ada celah data sekitar {missing} candle."
            )
            break

    recent_candles = ordered[-3:]

    if (
        len(recent_candles) == 3
        and all(
            candle.open
            == candle.high
            == candle.low
            == candle.close
            for candle in recent_candles
        )
    ):
        warnings.append(
            "Tiga candle terakhir memiliki OHLC datar; "
            "periksa kondisi pasar dan sumber data."
        )

    return warnings
