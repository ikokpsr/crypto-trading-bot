
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class MarketSnapshotStore:
    """Penyimpanan snapshot pasar untuk evaluasi read-only."""

    _FIELDS = {
        "timestamp_ms",
        "exchange",
        "symbol",
        "bid",
        "ask",
        "spread_pct",
        "quote_volume_idr",
        "net_profit_idr",
        "net_profit_pct",
    }

    _DECIMAL_FIELDS = (
        "bid",
        "ask",
        "spread_pct",
        "quote_volume_idr",
        "net_profit_idr",
        "net_profit_pct",
    )

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
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_ms INTEGER NOT NULL
                        CHECK (timestamp_ms > 0),
                    exchange TEXT NOT NULL
                        CHECK (length(trim(exchange)) > 0),
                    symbol TEXT NOT NULL
                        CHECK (length(trim(symbol)) > 0),
                    bid TEXT NOT NULL,
                    ask TEXT NOT NULL,
                    spread_pct TEXT NOT NULL,
                    quote_volume_idr TEXT NOT NULL,
                    net_profit_idr TEXT NOT NULL,
                    net_profit_pct TEXT NOT NULL,
                    CHECK (CAST(bid AS REAL) > 0),
                    CHECK (CAST(ask AS REAL) > 0),
                    CHECK (CAST(spread_pct AS REAL) >= 0),
                    CHECK (CAST(quote_volume_idr AS REAL) >= 0)
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_market_snapshots_symbol_timestamp
                ON market_snapshots (symbol, timestamp_ms)
                """
            )

    @staticmethod
    def _to_decimal(value: Any, field: str) -> Decimal:
        if isinstance(value, bool):
            raise ValueError(
                f"{field} harus berupa angka finite."
            )

        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(
                f"{field} harus berupa angka finite."
            ) from exc

        if not result.is_finite():
            raise ValueError(
                f"{field} harus berupa angka finite."
            )

        return result

    @classmethod
    def _validate_snapshot(
        cls,
        snapshot: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(snapshot, Mapping):
            raise ValueError("Snapshot harus berupa mapping.")

        missing = cls._FIELDS - snapshot.keys()

        if missing:
            raise ValueError(
                "Field snapshot tidak lengkap: "
                f"{', '.join(sorted(missing))}."
            )

        timestamp_ms = snapshot["timestamp_ms"]

        if (
            isinstance(timestamp_ms, bool)
            or not isinstance(timestamp_ms, int)
            or timestamp_ms <= 0
        ):
            raise ValueError(
                "timestamp_ms harus berupa integer positif."
            )

        normalized: dict[str, Any] = {
            "timestamp_ms": timestamp_ms,
        }

        for field in ("exchange", "symbol"):
            value = snapshot[field]

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field} tidak boleh kosong."
                )

            normalized[field] = value.strip()

        for field in cls._DECIMAL_FIELDS:
            normalized[field] = cls._to_decimal(
                snapshot[field],
                field,
            )

        if normalized["bid"] <= 0:
            raise ValueError("bid harus lebih besar dari nol.")

        if normalized["ask"] <= 0:
            raise ValueError("ask harus lebih besar dari nol.")

        if normalized["ask"] < normalized["bid"]:
            raise ValueError(
                "ask tidak boleh lebih kecil dari bid."
            )

        if normalized["spread_pct"] < 0:
            raise ValueError("spread_pct tidak boleh negatif.")

        if normalized["quote_volume_idr"] < 0:
            raise ValueError(
                "quote_volume_idr tidak boleh negatif."
            )

        return normalized

    def save_snapshot(
        self,
        snapshot: Mapping[str, Any],
    ) -> int:
        data = self._validate_snapshot(snapshot)

        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO market_snapshots (
                    timestamp_ms,
                    exchange,
                    symbol,
                    bid,
                    ask,
                    spread_pct,
                    quote_volume_idr,
                    net_profit_idr,
                    net_profit_pct
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["timestamp_ms"],
                    data["exchange"],
                    data["symbol"],
                    str(data["bid"]),
                    str(data["ask"]),
                    str(data["spread_pct"]),
                    str(data["quote_volume_idr"]),
                    str(data["net_profit_idr"]),
                    str(data["net_profit_pct"]),
                ),
            )

            return cursor.lastrowid

    
    def get_snapshots(
        self,
        symbol: str | None = None,
        limit: int = 100,
    ) -> tuple[dict[str, Any], ...]:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 1
        ):
            raise ValueError("limit minimal 1.")

        if symbol is not None and (
            not isinstance(symbol, str) or not symbol.strip()
        ):
            raise ValueError("symbol tidak boleh kosong.")

        with closing(self._connect()) as connection:
            if symbol is None:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM market_snapshots
                    ORDER BY timestamp_ms DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM market_snapshots
                    WHERE symbol = ?
                    ORDER BY timestamp_ms DESC, id DESC
                    LIMIT ?
                    """,
                    (symbol.strip(), limit),
                ).fetchall()

        # Batasi data dengan mengambil yang terbaru,
        # lalu kembalikan dalam urutan kronologis.
        result: list[dict[str, Any]] = []

        for row in reversed(rows):
            item = dict(row)

            for field in self._DECIMAL_FIELDS:
                item[field] = Decimal(item[field])

            result.append(item)

        return tuple(result)

