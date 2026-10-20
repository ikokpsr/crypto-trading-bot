import pytest

from app.config import load_settings


def test_default_trading_mode_is_paper(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ID", "binance")
    monkeypatch.delenv("TRADING_MODE", raising=False)

    settings = load_settings()

    assert settings.trading_mode == "PAPER"
    assert settings.market_type == "spot"
    assert settings.timeframe == "15m"


def test_live_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ID", "binance")
    monkeypatch.setenv("TRADING_MODE", "LIVE")

    with pytest.raises(ValueError, match="hanya boleh PAPER"):
        load_settings()


def test_non_spot_market_is_rejected(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ID", "binance")
    monkeypatch.setenv("MARKET_TYPE", "future")

    with pytest.raises(ValueError, match="wajib spot"):
        load_settings()


def test_unsupported_timeframe_is_rejected(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ID", "binance")
    monkeypatch.setenv("TIMEFRAME", "1h")

    with pytest.raises(ValueError, match="tidak didukung"):
        load_settings()


def test_invalid_telegram_user_id_is_rejected(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ID", "binance")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "abc")

    with pytest.raises(ValueError, match="ID numerik"):
        load_settings()

def test_scanner_configuration_defaults(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ID", "indodax")

    monkeypatch.delenv("SCANNER_MAX_SPREAD_PCT", raising=False)
    monkeypatch.delenv(
        "SCANNER_MIN_QUOTE_VOLUME_IDR",
        raising=False,
    )
    monkeypatch.delenv("SCANNER_ORDER_BUDGET_IDR", raising=False)

    settings = load_settings()

    assert settings.scanner_max_spread_pct == 0.3
    assert settings.scanner_min_quote_volume_idr == 10_000_000
    assert settings.scanner_order_budget_idr == 100_000


def test_invalid_scanner_configuration_is_rejected(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ID", "indodax")
    monkeypatch.setenv("SCANNER_ORDER_BUDGET_IDR", "0")

    with pytest.raises(
        ValueError,
        match="SCANNER_ORDER_BUDGET_IDR harus lebih besar dari nol",
    ):
        load_settings()

@pytest.mark.parametrize(
    "value",
    [
        "-1",
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_invalid_scanner_spread_is_rejected(monkeypatch, value):
    monkeypatch.setenv("EXCHANGE_ID", "indodax")
    monkeypatch.setenv("SCANNER_MAX_SPREAD_PCT", value)

    with pytest.raises(ValueError):
        load_settings()