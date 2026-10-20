from dataclasses import dataclass
from datetime import datetime, timezone
import math


TIMEFRAME_SECONDS = {
    "15m": 15 * 60,
}


@dataclass(frozen=True)
class Candle:
    exchange: str
    symbol: str
    timeframe: str
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if not isinstance(self.exchange, str) or not self.exchange.strip():
            raise ValueError("Exchange tidak boleh kosong.")

        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("Symbol tidak boleh kosong.")

        if not isinstance(self.timeframe, str) or self.timeframe not in TIMEFRAME_SECONDS:
            raise ValueError(
                f"Timeframe tidak didukung: {self.timeframe}"
            )

        if isinstance(self.timestamp_ms, bool) or not isinstance(
            self.timestamp_ms, int
        ):
            raise ValueError("Timestamp harus berupa bilangan bulat.")

        if self.timestamp_ms <= 0:
            raise ValueError("Timestamp harus positif.")

        values = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }

        for name, value in values.items():
            if not math.isfinite(value):
                raise ValueError(f"{name} harus berupa angka finite.")

        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("Harga harus lebih besar dari nol.")

        if self.volume < 0:
            raise ValueError("Volume tidak boleh negatif.")

        if self.high < max(self.open, self.close, self.low):
            raise ValueError("High tidak konsisten dengan OHLC.")

        if self.low > min(self.open, self.close, self.high):
            raise ValueError("Low tidak konsisten dengan OHLC.")

        interval_ms = TIMEFRAME_SECONDS[self.timeframe] * 1000

        if self.timestamp_ms % interval_ms != 0:
            raise ValueError(
                "Timestamp candle harus berada pada batas interval."
            )

    @property
    def open_time(self) -> datetime:
        return datetime.fromtimestamp(
            self.timestamp_ms / 1000,
            tz=timezone.utc,
        )

    @property
    def close_time_ms(self) -> int:
        return (
            self.timestamp_ms
            + TIMEFRAME_SECONDS[self.timeframe] * 1000
        )

    def is_closed(self, now_ms: int) -> bool:
        return now_ms >= self.close_time_ms
