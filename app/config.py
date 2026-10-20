
import math
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


SUPPORTED_TIMEFRAMES = {"15m"}


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    app_env: str
    trading_mode: str
    exchange_id: str
    market_type: str
    timeframe: str
    scanner_max_spread_pct: float
    scanner_min_quote_volume_idr: float
    scanner_order_budget_idr: float
    database_path: Path
    telegram_bot_token: str
    telegram_allowed_user_ids: tuple[int, ...]


def load_settings() -> Settings:
    trading_mode = _get_env("TRADING_MODE", "PAPER").upper()

    # Fail closed: mode selain PAPER tidak diizinkan.
    if trading_mode != "PAPER":
        raise ValueError(
            "TRADING_MODE hanya boleh PAPER pada fase awal."
        )

    market_type = _get_env("MARKET_TYPE", "spot").lower()
    if market_type != "spot":
        raise ValueError("MARKET_TYPE saat ini wajib spot.")

    timeframe = _get_env("TIMEFRAME", "15m")
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"TIMEFRAME tidak didukung: {timeframe}"
        )

    # Konfigurasi scanner.
    try:
        scanner_max_spread_pct = float(
            _get_env("SCANNER_MAX_SPREAD_PCT", "0.3")
        )
        scanner_min_quote_volume_idr = float(
            _get_env(
                "SCANNER_MIN_QUOTE_VOLUME_IDR",
                "10000000",
            )
        )
        scanner_order_budget_idr = float(
            _get_env("SCANNER_ORDER_BUDGET_IDR", "100000")
        )
    except ValueError as exc:
        raise ValueError(
            "Konfigurasi scanner harus berupa angka."
        ) from exc

    # Validasi konfigurasi scanner.
    scanner_values = (
        scanner_max_spread_pct,
        scanner_min_quote_volume_idr,
        scanner_order_budget_idr,
    )

    if not all(math.isfinite(value) for value in scanner_values):
        raise ValueError(
            "Konfigurasi scanner harus berupa angka finite."
        )

    if scanner_max_spread_pct <= 0:
        raise ValueError(
            "SCANNER_MAX_SPREAD_PCT harus lebih besar dari nol."
        )

    if scanner_min_quote_volume_idr < 0:
        raise ValueError(
            "SCANNER_MIN_QUOTE_VOLUME_IDR tidak boleh negatif."
        )

    if scanner_order_budget_idr <= 0:
        raise ValueError(
            "SCANNER_ORDER_BUDGET_IDR harus lebih besar dari nol."
        )

    # Konfigurasi exchange.
    exchange_id = _get_env("EXCHANGE_ID").lower()
    if not exchange_id:
        raise ValueError("EXCHANGE_ID wajib diisi.")

    # Konfigurasi Telegram.
    raw_user_ids = _get_env("TELEGRAM_ALLOWED_USER_IDS")
    user_ids: list[int] = []

    if raw_user_ids:
        try:
            user_ids = [
                int(value.strip())
                for value in raw_user_ids.split(",")
                if value.strip()
            ]
        except ValueError as exc:
            raise ValueError(
                "TELEGRAM_ALLOWED_USER_IDS harus berisi ID numerik."
            ) from exc

        if any(user_id <= 0 for user_id in user_ids):
            raise ValueError("Telegram user ID harus positif.")

    # Lokasi database.
    database_path = Path(
        _get_env("DATABASE_PATH", "data/bot.sqlite3")
    )

    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path

    return Settings(
        app_env=_get_env("APP_ENV", "development"),
        trading_mode=trading_mode,
        exchange_id=exchange_id,
        market_type=market_type,
        timeframe=timeframe,
        scanner_max_spread_pct=scanner_max_spread_pct,
        scanner_min_quote_volume_idr=scanner_min_quote_volume_idr,
        scanner_order_budget_idr=scanner_order_budget_idr,
        database_path=database_path,
        telegram_bot_token=_get_env("TELEGRAM_BOT_TOKEN"),
        telegram_allowed_user_ids=tuple(user_ids),
    )
