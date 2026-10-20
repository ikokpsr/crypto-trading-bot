
from __future__ import annotations

import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st

from app.config import load_settings


# ============================================================
# KONFIGURASI
# ============================================================

st.set_page_config(
    page_title="Crypto Bot Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOCAL_TZ = ZoneInfo("Asia/Jakarta")
MAX_DISPLAY_ROWS = 10_000
MAX_SCAN_HISTORY_ROWS = 500


# ============================================================
# DATABASE: MARKET SNAPSHOTS (READ-ONLY)
# ============================================================

@st.cache_data(ttl=10)
def load_snapshot_data(
    database_path: str,
) -> tuple[pd.DataFrame, dict[str, int | None]]:
    """Membaca snapshot pasar tanpa mengubah database."""

    path = Path(database_path).resolve()

    empty_df = pd.DataFrame(
        columns=[
            "id",
            "timestamp_ms",
            "exchange",
            "symbol",
            "bid",
            "ask",
            "spread_pct",
            "quote_volume_idr",
            "net_profit_idr",
            "net_profit_pct",
            "timestamp",
        ]
    )

    empty_stats: dict[str, int | None] = {
        "total_snapshots": 0,
        "total_symbols": 0,
        "latest_timestamp_ms": None,
        "oldest_timestamp_ms": None,
    }

    if not path.is_file():
        return empty_df, empty_stats

    uri = path.as_uri() + "?mode=ro"

    try:
        with sqlite3.connect(uri, uri=True, timeout=5) as connection:
            connection.execute("PRAGMA query_only = ON")

            table_exists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'market_snapshots'
                LIMIT 1
                """
            ).fetchone()

            if table_exists is None:
                return empty_df, empty_stats

            stats_row = connection.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(DISTINCT symbol),
                    MAX(timestamp_ms),
                    MIN(timestamp_ms)
                FROM market_snapshots
                """
            ).fetchone()

            stats = {
                "total_snapshots": int(stats_row[0] or 0),
                "total_symbols": int(stats_row[1] or 0),
                "latest_timestamp_ms": (
                    int(stats_row[2])
                    if stats_row[2] is not None
                    else None
                ),
                "oldest_timestamp_ms": (
                    int(stats_row[3])
                    if stats_row[3] is not None
                    else None
                ),
            }

            if stats["total_snapshots"] == 0:
                return empty_df, stats

            df = pd.read_sql_query(
                """
                SELECT
                    id,
                    timestamp_ms,
                    exchange,
                    symbol,
                    bid,
                    ask,
                    spread_pct,
                    quote_volume_idr,
                    net_profit_idr,
                    net_profit_pct
                FROM market_snapshots
                ORDER BY timestamp_ms DESC, id DESC
                LIMIT ?
                """,
                connection,
                params=(MAX_DISPLAY_ROWS,),
            )

    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Gagal membaca database snapshot: {exc}"
        ) from exc

    if df.empty:
        return empty_df, stats

    numeric_columns = [
        "timestamp_ms",
        "bid",
        "ask",
        "spread_pct",
        "quote_volume_idr",
        "net_profit_idr",
        "net_profit_pct",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["timestamp"] = (
        pd.to_datetime(
            df["timestamp_ms"],
            unit="ms",
            utc=True,
            errors="coerce",
        )
        .dt.tz_convert(LOCAL_TZ)
    )

    df = df.dropna(
        subset=[
            "timestamp",
            "symbol",
            "net_profit_idr",
            "net_profit_pct",
        ]
    )

    return df, stats


# ============================================================
# DATABASE: SCAN DIAGNOSTICS (READ-ONLY)
# ============================================================

@st.cache_data(ttl=10)
def load_scan_diagnostics(database_path: str) -> pd.DataFrame:
    """Membaca riwayat scanner tanpa menjalankan scanner."""

    columns = [
        "id",
        "started_at_ms",
        "finished_at_ms",
        "duration_ms",
        "status",
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
        "error_type",
        "error_message",
    ]

    empty_df = pd.DataFrame(columns=columns)
    path = Path(database_path).resolve()

    if not path.is_file():
        return empty_df

    uri = path.as_uri() + "?mode=ro"

    try:
        with sqlite3.connect(uri, uri=True, timeout=5) as connection:
            connection.execute("PRAGMA query_only = ON")

            table_exists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'scan_runs'
                LIMIT 1
                """
            ).fetchone()

            if table_exists is None:
                return empty_df

            df = pd.read_sql_query(
                """
                SELECT
                    id,
                    started_at_ms,
                    finished_at_ms,
                    duration_ms,
                    status,
                    candidates_found,
                    order_books_attempted,
                    order_books_failed,
                    invalid_order_books,
                    invalid_market_metadata,
                    insufficient_depth,
                    estimation_errors,
                    below_profit_target,
                    profitable_candidates,
                    snapshots_saved,
                    snapshot_save_failures,
                    error_type,
                    error_message
                FROM scan_runs
                ORDER BY started_at_ms DESC, id DESC
                LIMIT ?
                """,
                connection,
                params=(MAX_SCAN_HISTORY_ROWS,),
            )

    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Gagal membaca riwayat diagnostik scanner: {exc}"
        ) from exc

    if df.empty:
        return empty_df

    numeric_columns = [
        "id",
        "started_at_ms",
        "finished_at_ms",
        "duration_ms",
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
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["started_at"] = (
        pd.to_datetime(
            df["started_at_ms"],
            unit="ms",
            utc=True,
            errors="coerce",
        )
        .dt.tz_convert(LOCAL_TZ)
    )

    df["finished_at"] = (
        pd.to_datetime(
            df["finished_at_ms"],
            unit="ms",
            utc=True,
            errors="coerce",
        )
        .dt.tz_convert(LOCAL_TZ)
    )

    return df


# ============================================================
# HELPER
# ============================================================

def format_rupiah(value: float | int) -> str:
    return f"Rp{value:,.2f}"


def format_timestamp(timestamp_ms: int | None) -> str:
    if timestamp_ms is None:
        return "Belum ada data"

    timestamp = pd.to_datetime(
        timestamp_ms,
        unit="ms",
        utc=True,
    ).tz_convert(LOCAL_TZ)

    return timestamp.strftime("%d-%m-%Y %H:%M:%S WIB")


def safe_int(value: object) -> int:
    numeric = pd.to_numeric(value, errors="coerce")

    if pd.isna(numeric):
        return 0

    return int(numeric)


# ============================================================
# HEADER DAN VALIDASI MODE
# ============================================================

st.title("📊 Crypto Trading Bot")
st.caption(
    "Dashboard evaluasi market Indodax, snapshot pasar, "
    "dan diagnostik scanner."
)

try:
    settings = load_settings()
except (ValueError, OSError) as exc:
    st.error(f"Konfigurasi aplikasi tidak valid: {exc}")
    st.stop()

if settings.trading_mode != "PAPER":
    st.error(
        "Dashboard hanya mengizinkan mode PAPER. "
        "Periksa konfigurasi aplikasi sebelum melanjutkan."
    )
    st.stop()

with st.sidebar:
    st.header("Pengaturan")

    st.success("Mode: PAPER")
    st.write(f"Exchange: `{settings.exchange_id}`")
    st.write(f"Market: `{settings.market_type}`")
    st.write(f"Timeframe: `{settings.timeframe}`")

    st.caption("Dashboard hanya membaca data tersimpan.")
    st.caption("Tidak ada order yang dikirim.")
    st.caption("Halaman ini tidak menjalankan scan otomatis.")

    if st.button("🔄 Muat ulang data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Database")
    st.code(str(settings.database_path), language="text")


# ============================================================
# MEMUAT DATA
# ============================================================

try:
    df, stats = load_snapshot_data(str(settings.database_path))
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

try:
    scan_df = load_scan_diagnostics(str(settings.database_path))
except RuntimeError as exc:
    st.error(str(exc))
    scan_df = pd.DataFrame()


# ============================================================
# BAGIAN 1: DIAGNOSTIK SCANNER
# ============================================================

st.header("Diagnostik Scanner")
st.caption(
    "Ringkasan pemindaian berdasarkan riwayat tersimpan. "
    "Dashboard tidak menjalankan scanner."
)

if scan_df.empty:
    st.info(
        "Belum ada riwayat scan yang tersedia. "
        "Pastikan scanner menyimpan riwayat ke tabel scan_runs."
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Riwayat scan dimuat", 0)
    col2.metric("Kandidat terakhir", 0)
    col3.metric("Peluang profitable", 0)
    col4.metric("Durasi terakhir", "Belum ada")

else:
    latest_scan = scan_df.iloc[0]

    total_scans = len(scan_df)
    completed_scans = int(
        (scan_df["status"] == "completed").sum()
    )
    failed_scans = int(
        (scan_df["status"] == "failed").sum()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Riwayat scan dimuat", f"{total_scans:,}")
    col2.metric(
        "Kandidat scan terakhir",
        f"{safe_int(latest_scan['candidates_found']):,}",
    )
    col3.metric(
        "Peluang profitable terakhir",
        f"{safe_int(latest_scan['profitable_candidates']):,}",
    )
    col4.metric(
        "Durasi scan terakhir",
        f"{safe_int(latest_scan['duration_ms']):,} ms",
    )

    if pd.notna(latest_scan["started_at"]):
        st.caption(
            "Waktu scan terakhir: "
            f"{latest_scan['started_at'].strftime('%d-%m-%Y %H:%M:%S WIB')}"
        )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Scan completed", f"{completed_scans:,}")
    col2.metric("Scan failed", f"{failed_scans:,}")
    col3.metric(
        "Order book diperiksa",
        f"{safe_int(latest_scan['order_books_attempted']):,}",
    )
    col4.metric(
        "Snapshot tersimpan",
        f"{safe_int(latest_scan['snapshots_saved']):,}",
    )

    if latest_scan["status"] == "failed":
        st.error(
            "Scan terakhir berstatus FAILED. "
            f"Tipe error: {latest_scan['error_type'] or 'Tidak diketahui'}. "
            f"Pesan: {latest_scan['error_message'] or 'Tidak ada detail error'}"
        )

    st.divider()
    st.subheader("Hasil pemeriksaan scan terakhir")

    rejection_labels = {
        "Order book gagal": "order_books_failed",
        "Order book tidak valid": "invalid_order_books",
        "Metadata market tidak valid": "invalid_market_metadata",
        "Kedalaman order book kurang": "insufficient_depth",
        "Error estimasi": "estimation_errors",
        "Di bawah target profit": "below_profit_target",
    }

    rejection_data = pd.DataFrame(
        [
            {
                "Kategori": label,
                "Jumlah": safe_int(latest_scan[column]),
            }
            for label, column in rejection_labels.items()
        ]
    ).sort_values("Jumlah", ascending=True)

    fig_rejections = px.bar(
        rejection_data,
        x="Jumlah",
        y="Kategori",
        orientation="h",
        text="Jumlah",
        title="Kategori diagnostik pada scan terakhir",
    )

    fig_rejections.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    st.plotly_chart(
        fig_rejections,
        width="stretch",
    )

    st.caption(
        "Kategori diagnostik bukan selalu jumlah kandidat unik. "
        "Satu kandidat dapat melewati beberapa tahap pemeriksaan."
    )

    st.divider()
    st.subheader("Tren diagnostik")

    trend_df = scan_df.dropna(
        subset=["started_at"]
    ).sort_values(
        ["started_at_ms", "id"]
    ).copy()

    trend_metric = st.selectbox(
        "Metrik tren",
        options=[
            "Jumlah kandidat",
            "Peluang profitable",
            "Order book diperiksa",
            "Order book gagal",
            "Durasi scan (ms)",
            "Snapshot tersimpan",
        ],
    )

    trend_mapping = {
        "Jumlah kandidat": (
            "candidates_found",
            "Jumlah kandidat",
        ),
        "Peluang profitable": (
            "profitable_candidates",
            "Jumlah peluang profitable",
        ),
        "Order book diperiksa": (
            "order_books_attempted",
            "Jumlah order book diperiksa",
        ),
        "Order book gagal": (
            "order_books_failed",
            "Jumlah order book gagal",
        ),
        "Durasi scan (ms)": (
            "duration_ms",
            "Durasi scan (ms)",
        ),
        "Snapshot tersimpan": (
            "snapshots_saved",
            "Jumlah snapshot tersimpan",
        ),
    }

    trend_column, trend_title = trend_mapping[trend_metric]

    if not trend_df.empty:
        fig_trend = px.line(
            trend_df,
            x="started_at",
            y=trend_column,
            markers=True,
            title=trend_title,
            labels={
                "started_at": "Waktu scan (WIB)",
                trend_column: trend_title,
            },
        )

        fig_trend.update_layout(
            hovermode="x unified",
            margin=dict(l=10, r=10, t=50, b=10),
        )

        st.plotly_chart(
            fig_trend,
            width="stretch",
        )
    else:
        st.info("Waktu scan tidak tersedia untuk membuat grafik tren.")

    st.divider()
    st.subheader("Riwayat scan")

    history_columns = [
        "id",
        "started_at",
        "duration_ms",
        "status",
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
        "error_type",
        "error_message",
    ]

    history_df = scan_df[history_columns].copy().rename(
        columns={
            "id": "ID",
            "started_at": "Waktu (WIB)",
            "duration_ms": "Durasi (ms)",
            "status": "Status",
            "candidates_found": "Kandidat",
            "order_books_attempted": "Order book diperiksa",
            "order_books_failed": "Order book gagal",
            "invalid_order_books": "Order book tidak valid",
            "invalid_market_metadata": "Metadata tidak valid",
            "insufficient_depth": "Depth kurang",
            "estimation_errors": "Error estimasi",
            "below_profit_target": "Di bawah target",
            "profitable_candidates": "Profitable",
            "snapshots_saved": "Snapshot tersimpan",
            "snapshot_save_failures": "Gagal simpan snapshot",
            "error_type": "Tipe error",
            "error_message": "Pesan error",
        }
    )

    st.dataframe(
        history_df,
        width="stretch",
        hide_index=True,
        height=400,
    )

    st.download_button(
        label="Ekspor riwayat scan ke CSV",
        data=history_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="scan_diagnostics.csv",
        mime="text/csv",
        width="stretch",
    )

st.divider()


# ============================================================
# BAGIAN 2: SNAPSHOT PASAR
# ============================================================

st.header("Snapshot Pasar")

if stats["total_snapshots"] == 0 or df.empty:
    st.info(
        "Belum ada snapshot pasar yang dapat ditampilkan. "
        "Bagian diagnostik scanner tetap tersedia."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total snapshot", f"{stats['total_snapshots']:,}")
    col2.metric("Market tercatat", f"{stats['total_symbols']:,}")
    col3.metric(
        "Snapshot terbaru",
        format_timestamp(stats["latest_timestamp_ms"]),
    )

else:
    if stats["total_snapshots"] > MAX_DISPLAY_ROWS:
        st.warning(
            f"Database berisi {stats['total_snapshots']:,} snapshot. "
            f"Tabel dan grafik hanya memuat maksimal "
            f"{MAX_DISPLAY_ROWS:,} snapshot terbaru."
        )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total snapshot",
        f"{stats['total_snapshots']:,}",
    )
    col2.metric(
        "Market tercatat",
        f"{stats['total_symbols']:,}",
    )
    col3.metric(
        "Snapshot terbaru",
        format_timestamp(stats["latest_timestamp_ms"]),
    )

    st.divider()
    st.subheader("Filter data")

    symbols = sorted(df["symbol"].dropna().unique().tolist())

    filter_col1, filter_col2 = st.columns([1, 2])

    with filter_col1:
        selected_symbols = st.multiselect(
            "Pilih simbol",
            options=symbols,
            default=symbols,
            help="Kosongkan pilihan untuk menampilkan tanpa data.",
        )

    with filter_col2:
        valid_dates = df["timestamp"].dropna().dt.date

        if valid_dates.empty:
            date_range = None
        else:
            date_range = st.date_input(
                "Rentang tanggal (WIB)",
                value=(min(valid_dates), max(valid_dates)),
                min_value=min(valid_dates),
                max_value=max(valid_dates),
            )

    filtered_df = df.copy()

    if selected_symbols:
        filtered_df = filtered_df[
            filtered_df["symbol"].isin(selected_symbols)
        ]
    else:
        filtered_df = filtered_df.iloc[0:0]

    if date_range:
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_dates = filtered_df["timestamp"].dt.date

            filtered_df = filtered_df[
                (filtered_dates >= start_date)
                & (filtered_dates <= end_date)
            ]

        elif isinstance(date_range, (tuple, list)) and len(date_range) == 1:
            selected_date = date_range[0]

            filtered_df = filtered_df[
                filtered_df["timestamp"].dt.date == selected_date
            ]

    if filtered_df.empty:
        st.warning("Tidak ada snapshot untuk filter yang dipilih.")

    else:
        latest_rows = filtered_df.sort_values(
            ["timestamp_ms", "id"],
            ascending=[False, False],
        )

        latest_row = latest_rows.iloc[0]

        best_row = filtered_df.loc[
            filtered_df["net_profit_pct"].idxmax()
        ]

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Snapshot sesuai filter",
            f"{len(filtered_df):,}",
        )

        col2.metric(
            "Estimasi profit terbaru",
            format_rupiah(float(latest_row["net_profit_idr"])),
            help=(
                f"{latest_row['symbol']} — "
                f"{latest_row['net_profit_pct']:.4f}%"
            ),
        )

        col3.metric(
            "Profit % tertinggi dalam data",
            f"{best_row['net_profit_pct']:.4f}%",
            help=(
                f"{best_row['symbol']} — "
                f"{format_rupiah(float(best_row['net_profit_idr']))}"
            ),
        )

        st.caption(
            "Profit adalah estimasi historis per snapshot, bukan profit "
            "yang sudah direalisasikan. Hasil aktual dapat berbeda akibat "
            "biaya, slippage, likuiditas, dan perubahan harga."
        )

        st.divider()
        st.subheader("Grafik estimasi profit bersih")

        chart_metric = st.radio(
            "Metrik grafik",
            options=[
                "Profit bersih (IDR)",
                "Profit bersih (%)",
                "Spread (%)",
            ],
            horizontal=True,
        )

        metric_mapping = {
            "Profit bersih (IDR)": (
                "net_profit_idr",
                "Estimasi profit bersih (IDR)",
            ),
            "Profit bersih (%)": (
                "net_profit_pct",
                "Estimasi profit bersih (%)",
            ),
            "Spread (%)": (
                "spread_pct",
                "Spread (%)",
            ),
        }

        y_column, y_title = metric_mapping[chart_metric]

        chart_df = filtered_df.sort_values(
            ["timestamp_ms", "id"]
        ).copy()

        figure = px.line(
            chart_df,
            x="timestamp",
            y=y_column,
            color="symbol",
            markers=True,
            title=y_title,
            labels={
                "timestamp": "Waktu (WIB)",
                y_column: y_title,
                "symbol": "Simbol",
            },
        )

        figure.update_layout(
            hovermode="x unified",
            legend_title_text="Simbol",
            margin=dict(l=10, r=10, t=50, b=10),
        )

        st.plotly_chart(
            figure,
            width="stretch",
        )

        st.divider()
        st.subheader("Riwayat snapshot")

        display_df = latest_rows[
            [
                "timestamp",
                "exchange",
                "symbol",
                "bid",
                "ask",
                "spread_pct",
                "quote_volume_idr",
                "net_profit_idr",
                "net_profit_pct",
            ]
        ].copy().rename(
            columns={
                "timestamp": "Waktu (WIB)",
                "exchange": "Exchange",
                "symbol": "Simbol",
                "bid": "Bid",
                "ask": "Ask",
                "spread_pct": "Spread (%)",
                "quote_volume_idr": "Volume quote (IDR)",
                "net_profit_idr": "Estimasi profit (IDR)",
                "net_profit_pct": "Estimasi profit (%)",
            }
        )

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            height=450,
            column_config={
                "Bid": st.column_config.NumberColumn(
                    format="Rp%.8f",
                ),
                "Ask": st.column_config.NumberColumn(
                    format="Rp%.8f",
                ),
                "Spread (%)": st.column_config.NumberColumn(
                    format="%.4f%%",
                ),
                "Volume quote (IDR)": st.column_config.NumberColumn(
                    format="Rp%.2f",
                ),
                "Estimasi profit (IDR)": st.column_config.NumberColumn(
                    format="Rp%.2f",
                ),
                "Estimasi profit (%)": st.column_config.NumberColumn(
                    format="%.4f%%",
                ),
            },
        )

        st.download_button(
            label="Ekspor snapshot terfilter ke CSV",
            data=display_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="market_snapshots.csv",
            mime="text/csv",
            width="stretch",
        )

st.divider()

st.caption(
    "Mode PAPER — dashboard hanya membaca database. "
    "Tidak ada order yang dikirim dan tidak ada scan otomatis. "
    "Estimasi profit bukan jaminan keuntungan aktual."
)
