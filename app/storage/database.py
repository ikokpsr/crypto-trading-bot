
import sqlite3
from pathlib import Path
from collections.abc import Sequence

from app.domain.candle import Candle


class CandleStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(
            self.database_path,
            timeout=10.0,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS candles (
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp_ms INTEGER NOT NULL,
                    open REAL NOT NULL CHECK (open > 0),
                    high REAL NOT NULL CHECK (high > 0),
                    low REAL NOT NULL CHECK (low > 0),
                    close REAL NOT NULL CHECK (close > 0),
                    volume REAL NOT NULL CHECK (volume >= 0),

                    PRIMARY KEY (
                        exchange,
                        symbol,
                        timeframe,
                        timestamp_ms
                    )
                )
                """
            )

    def save_closed_candles(
        self,
        candles: Sequence[Candle],
        now_ms: int,
    ) -> int:
        """
        Simpan candle yang sudah ditutup.
        Mengembalikan jumlah candle yang diproses,
        bukan jumlah baris baru yang dibuat.
        """
        for candle in candles:
            if not candle.is_closed(now_ms):
                raise ValueError(
                    "Candle yang belum ditutup tidak boleh disimpan."
                )

        if not candles:
            return 0

        rows = [
            (
                candle.exchange,
                candle.symbol,
                candle.timeframe,
                candle.timestamp_ms,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
            )
            for candle in candles
        ]

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO candles (
                    exchange,
                    symbol,
                    timeframe,
                    timestamp_ms,
                    open,
                    high,
                    low,
                    close,
                    volume
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (
                    exchange,
                    symbol,
                    timeframe,
                    timestamp_ms
                )
                DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
                """,
                rows,
            )

        return len(rows)

    def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> tuple[Candle, ...]:
        if limit < 1:
            raise ValueError("limit minimal 1.")

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    exchange,
                    symbol,
                    timeframe,
                    timestamp_ms,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM candles
                WHERE exchange = ?
                  AND symbol = ?
                  AND timeframe = ?
                ORDER BY timestamp_ms DESC
                LIMIT ?
                """,
                (exchange, symbol, timeframe, limit),
            ).fetchall()

        # Query mengambil data terbaru dahulu untuk membatasi
        # jumlah baris. Balik urutan agar hasil kronologis.
        return tuple(
            Candle(
                exchange=row["exchange"],
                symbol=row["symbol"],
                timeframe=row["timeframe"],
                timestamp_ms=row["timestamp_ms"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
            for row in reversed(rows)
        )
