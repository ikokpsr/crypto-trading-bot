
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Any


class ScanDiagnosticsStore:
    """Penyimpanan riwayat diagnostik scanner menggunakan SQLite."""

    COUNTER_FIELDS = (
        "candidates_found",
        "order_books_attempted",
        "order_books_failed",
        "invalid_order_books",
        "invalid_market_metadata",
        "insufficient_depth",
        "estimation_errors",
        "below_profit_target",
        "profitable_candidates",
        "snapshots_saved",
        "snapshot_save_failures",
    )

    REQUIRED_FIELDS = (
        "started_at_ms",
        "finished_at_ms",
        "duration_ms",
        "status",
        *COUNTER_FIELDS,
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
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at_ms INTEGER NOT NULL,
                    finished_at_ms INTEGER NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    status TEXT NOT NULL
                        CHECK (status IN ('completed', 'failed')),

                    candidates_found INTEGER NOT NULL DEFAULT 0,
                    order_books_attempted INTEGER NOT NULL DEFAULT 0,
                    order_books_failed INTEGER NOT NULL DEFAULT 0,
                    invalid_order_books INTEGER NOT NULL DEFAULT 0,
                    invalid_market_metadata INTEGER NOT NULL DEFAULT 0,
                    insufficient_depth INTEGER NOT NULL DEFAULT 0,
                    estimation_errors INTEGER NOT NULL DEFAULT 0,
                    below_profit_target INTEGER NOT NULL DEFAULT 0,
                    profitable_candidates INTEGER NOT NULL DEFAULT 0,
                    snapshots_saved INTEGER NOT NULL DEFAULT 0,
                    snapshot_save_failures INTEGER NOT NULL DEFAULT 0,

                    error_type TEXT,
                    error_message TEXT,

                    CHECK (started_at_ms >= 0),
                    CHECK (finished_at_ms >= started_at_ms),
                    CHECK (duration_ms >= 0)
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_scan_runs_started_at
                ON scan_runs(started_at_ms DESC, id DESC)
                """
            )

            connection.commit()

    @classmethod
    def _validate_run(
        cls,
        run: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(run, Mapping):
            raise ValueError("Data scan harus berupa mapping.")

        missing = [
            field
            for field in cls.REQUIRED_FIELDS
            if field not in run
        ]

        if missing:
            raise ValueError(
                f"Field scan wajib tidak ditemukan: {', '.join(missing)}"
            )

        validated = dict(run)

        for field in (
            "started_at_ms",
            "finished_at_ms",
            "duration_ms",
            *cls.COUNTER_FIELDS,
        ):
            value = validated[field]

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field} harus berupa integer nonnegatif."
                )

        if validated["finished_at_ms"] < validated["started_at_ms"]:
            raise ValueError(
                "finished_at_ms tidak boleh sebelum started_at_ms."
            )

        if validated["duration_ms"] != (
            validated["finished_at_ms"] - validated["started_at_ms"]
        ):
            raise ValueError(
                "duration_ms harus sesuai selisih waktu mulai dan selesai."
            )

        if validated["status"] not in ("completed", "failed"):
            raise ValueError(
                "status harus 'completed' atau 'failed'."
            )

        for field in ("error_type", "error_message"):
            value = validated.get(field)

            if value is not None and not isinstance(value, str):
                raise ValueError(
                    f"{field} harus berupa string atau None."
                )

        if validated["status"] == "completed":
            validated["error_type"] = None
            validated["error_message"] = None

        return validated

    def save_run(self, run: Mapping[str, Any]) -> int:
        """Simpan satu proses scan dan kembalikan ID riwayatnya."""
        data = self._validate_run(run)

        columns = (
            "started_at_ms",
            "finished_at_ms",
            "duration_ms",
            "status",
            *self.COUNTER_FIELDS,
            "error_type",
            "error_message",
        )

        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        values = tuple(data.get(column, 0) for column in columns)

        with closing(self._connect()) as connection:
            cursor = connection.execute(
                f"""
                INSERT INTO scan_runs ({column_sql})
                VALUES ({placeholders})
                """,
                values,
            )
            connection.commit()

            return int(cursor.lastrowid)

    def get_runs(
        self,
        limit: int = 100,
        status: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Ambil riwayat terbaru, ditampilkan dari yang lama ke baru."""
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 1
        ):
            raise ValueError("limit minimal 1.")

        if status is not None and status not in (
            "completed",
            "failed",
        ):
            raise ValueError(
                "status harus 'completed', 'failed', atau None."
            )

        with closing(self._connect()) as connection:
            if status is None:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM scan_runs
                    ORDER BY started_at_ms DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM scan_runs
                    WHERE status = ?
                    ORDER BY started_at_ms DESC, id DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()

        return tuple(dict(row) for row in reversed(rows))
