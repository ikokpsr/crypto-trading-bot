
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from time import time
from typing import Any

from app.config import load_settings
from app.scanner.execution_estimator import (
    DEFAULT_MIN_ORDER_COST,
    TARGET_NET_PROFIT_PCT,
    estimate_round_trip,
)
from app.scanner.indodax_scanner import IndodaxScanner
from app.storage.market_snapshot_store import MarketSnapshotStore
from app.storage.scan_diagnostics_store import ScanDiagnosticsStore


@dataclass(frozen=True)
class ProfitableCandidate:
    symbol: str
    buy_cost: Decimal
    buy_fee: Decimal
    sell_proceeds: Decimal
    sell_fee: Decimal
    net_profit: Decimal
    net_profit_pct: Decimal


@dataclass
class ScanDiagnostics:
    candidates_found: int = 0
    order_books_attempted: int = 0
    order_books_failed: int = 0
    invalid_order_books: int = 0
    invalid_market_metadata: int = 0
    insufficient_depth: int = 0
    estimation_errors: int = 0
    below_profit_target: int = 0
    profitable_candidates: int = 0
    snapshots_saved: int = 0
    snapshot_save_failures: int = 0


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        result = Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError):
        return None

    if not result.is_finite():
        return None

    return result


def _decimal_order_book(levels: Any) -> list[list[Decimal]]:
    """Konversi level order book CCXT menjadi Decimal."""
    result: list[list[Decimal]] = []

    if not isinstance(levels, (list, tuple)):
        return result

    for level in levels:
        if not isinstance(level, (list, tuple)) or len(level) < 2:
            continue

        price = _to_decimal(level[0])
        amount = _to_decimal(level[1])

        if (
            price is None
            or amount is None
            or price <= 0
            or amount <= 0
        ):
            continue

        result.append([price, amount])

    return result


class ProfitabilityScanner:
    """Evaluator peluang round-trip tanpa mengirim order."""

    def __init__(
        self,
        scanner: IndodaxScanner | None = None,
        *,
        max_order_books: int = 20,
        target_net_profit_pct: Decimal = TARGET_NET_PROFIT_PCT,
        snapshot_store: MarketSnapshotStore | None = None,
        diagnostics_store: ScanDiagnosticsStore | None = None,
    ) -> None:
        if (
            isinstance(max_order_books, bool)
            or not isinstance(max_order_books, int)
            or max_order_books < 1
        ):
            raise ValueError(
                "max_order_books harus berupa integer positif."
            )

        if (
            not isinstance(target_net_profit_pct, Decimal)
            or not target_net_profit_pct.is_finite()
            or target_net_profit_pct < 0
        ):
            raise ValueError(
                "Target profit harus berupa Decimal finite "
                "dan tidak negatif."
            )

        self.settings = load_settings()
        self.order_budget = Decimal(
            str(self.settings.scanner_order_budget_idr)
        )

        if (
            not self.order_budget.is_finite()
            or self.order_budget <= 0
        ):
            raise ValueError("Budget order harus lebih besar dari nol.")

        self.scanner = (
            scanner if scanner is not None else IndodaxScanner()
        )
        self.max_order_books = max_order_books
        self.target_net_profit_pct = target_net_profit_pct

        self.snapshot_store = (
            snapshot_store
            if snapshot_store is not None
            else MarketSnapshotStore(self.settings.database_path)
        )
        self.snapshot_store.initialize()

        self.diagnostics_store = (
            diagnostics_store
            if diagnostics_store is not None
            else ScanDiagnosticsStore(self.settings.database_path)
        )
        self.diagnostics_store.initialize()

        self.last_diagnostics = ScanDiagnostics()

    def scan_once(self) -> list[ProfitableCandidate]:
        """Jalankan satu scan dan simpan ringkasan diagnostiknya."""
        diagnostics = ScanDiagnostics()
        self.last_diagnostics = diagnostics

        started_at_ms = int(time() * 1000)

        try:
            opportunities = self._scan_once(diagnostics)
        except Exception as exc:
            finished_at_ms = int(time() * 1000)

            self._save_scan_diagnostics(
                diagnostics=diagnostics,
                started_at_ms=started_at_ms,
                finished_at_ms=finished_at_ms,
                status="failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise

        finished_at_ms = int(time() * 1000)

        self._save_scan_diagnostics(
            diagnostics=diagnostics,
            started_at_ms=started_at_ms,
            finished_at_ms=finished_at_ms,
            status="completed",
        )

        return opportunities

    def _save_scan_diagnostics(
        self,
        *,
        diagnostics: ScanDiagnostics,
        started_at_ms: int,
        finished_at_ms: int,
        status: str,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Simpan ringkasan scan tanpa menutupi hasil atau error scan."""
        run = {
            "started_at_ms": started_at_ms,
            "finished_at_ms": finished_at_ms,
            "duration_ms": max(
                0,
                finished_at_ms - started_at_ms,
            ),
            "status": status,
            **vars(diagnostics),
            "error_type": error_type,
            "error_message": (
                error_message[:1000]
                if error_message is not None
                else None
            ),
        }

        try:
            self.diagnostics_store.save_run(run)
        except Exception as exc:
            print(
                "[DIAGNOSTIK SCAN GAGAL DISIMPAN] "
                f"{type(exc).__name__}: {exc}"
            )

    def _scan_once(
        self,
        diagnostics: ScanDiagnostics,
    ) -> list[ProfitableCandidate]:
        candidates = self.scanner.scan_once()
        diagnostics.candidates_found = len(candidates)

        exchange = self.scanner.exchange
        markets = self.scanner._markets or {}

        opportunities: list[ProfitableCandidate] = []

        ranked_candidates = sorted(
            candidates,
            key=lambda candidate: (
                candidate.spread_pct,
                -(
                    candidate.quote_volume
                    if candidate.quote_volume is not None
                    else Decimal("0")
                ),
            ),
        )

        selected_candidates = ranked_candidates[
            :self.max_order_books
        ]

        for candidate in selected_candidates:
            market = markets.get(candidate.symbol)

            if not isinstance(market, Mapping):
                diagnostics.invalid_market_metadata += 1
                continue

            diagnostics.order_books_attempted += 1

            try:
                order_book = exchange.fetch_order_book(
                    candidate.symbol,
                    limit=20,
                )
            except Exception as exc:
                diagnostics.order_books_failed += 1
                print(
                    f"[ORDER BOOK GAGAL] {candidate.symbol}: "
                    f"{type(exc).__name__}: {exc}"
                )
                continue

            if not isinstance(order_book, Mapping):
                diagnostics.invalid_order_books += 1
                continue

            asks = _decimal_order_book(order_book.get("asks"))
            bids = _decimal_order_book(order_book.get("bids"))

            if not asks or not bids:
                diagnostics.invalid_order_books += 1
                continue

            precision = market.get("precision")
            limits = market.get("limits")

            if not isinstance(precision, Mapping):
                diagnostics.invalid_market_metadata += 1
                continue

            if not isinstance(limits, Mapping):
                diagnostics.invalid_market_metadata += 1
                continue

            amount_limits = limits.get("amount")
            cost_limits = limits.get("cost")

            if not isinstance(amount_limits, Mapping):
                diagnostics.invalid_market_metadata += 1
                continue

            if cost_limits is None:
                cost_limits = {}
            elif not isinstance(cost_limits, Mapping):
                diagnostics.invalid_market_metadata += 1
                continue

            amount_step = _to_decimal(precision.get("amount"))
            min_amount = _to_decimal(amount_limits.get("min"))
            min_cost = _to_decimal(cost_limits.get("min"))

            if amount_step is None or amount_step <= 0:
                diagnostics.invalid_market_metadata += 1
                continue

            if min_amount is None or min_amount < 0:
                diagnostics.invalid_market_metadata += 1
                continue

            # Kebijakan aplikasi, bukan minimum resmi exchange.
            if min_cost is None:
                min_cost = DEFAULT_MIN_ORDER_COST
            elif min_cost < 0:
                diagnostics.invalid_market_metadata += 1
                continue

            try:
                estimate = estimate_round_trip(
                    asks,
                    bids,
                    budget=self.order_budget,
                    amount_step=amount_step,
                    min_amount=min_amount,
                    min_cost=min_cost,
                )
            except (ValueError, ArithmeticError) as exc:
                error_message = str(exc)

                if "crossed order book" in error_message.lower():
                    diagnostics.invalid_order_books += 1
                else:
                    diagnostics.estimation_errors += 1

                print(
                    f"[ESTIMASI TIDAK VALID] "
                    f"{candidate.symbol}: {exc}"
                )
                continue

            if estimate is None:
                diagnostics.insufficient_depth += 1
                print(
                    f"[ESTIMASI DITOLAK] {candidate.symbol}: "
                    "kedalaman atau batas minimum order tidak terpenuhi."
                )
                continue

            print(
                f"[DIAGNOSTIK] {candidate.symbol} | "
                f"Beli: Rp{estimate.buy_cost:,.2f} | "
                f"Fee beli: Rp{estimate.buy_fee:,.2f} | "
                f"Hasil jual: Rp{estimate.sell_proceeds:,.2f} | "
                f"Fee jual: Rp{estimate.sell_fee:,.2f} | "
                f"Profit bersih: Rp{estimate.net_profit:,.2f} | "
                f"Profit: {estimate.net_profit_pct:.4f}%"
            )

            snapshot = {
                "timestamp_ms": int(time() * 1000),
                "exchange": self.settings.exchange_id,
                "symbol": candidate.symbol,
                "bid": bids[0][0],
                "ask": asks[0][0],
                "spread_pct": candidate.spread_pct,
                "quote_volume_idr": (
                    candidate.quote_volume
                    if candidate.quote_volume is not None
                    else Decimal("0")
                ),
                "net_profit_idr": estimate.net_profit,
                "net_profit_pct": estimate.net_profit_pct,
            }

            try:
                self.snapshot_store.save_snapshot(snapshot)
                diagnostics.snapshots_saved += 1
            except Exception as exc:
                diagnostics.snapshot_save_failures += 1
                print(
                    f"[SNAPSHOT GAGAL] {candidate.symbol}: "
                    f"{type(exc).__name__}: {exc}"
                )

            if estimate.net_profit_pct < self.target_net_profit_pct:
                diagnostics.below_profit_target += 1
                continue

            opportunities.append(
                ProfitableCandidate(
                    symbol=candidate.symbol,
                    buy_cost=estimate.buy_cost,
                    buy_fee=estimate.buy_fee,
                    sell_proceeds=estimate.sell_proceeds,
                    sell_fee=estimate.sell_fee,
                    net_profit=estimate.net_profit,
                    net_profit_pct=estimate.net_profit_pct,
                )
            )

        opportunities.sort(
            key=lambda item: item.net_profit_pct,
            reverse=True,
        )

        diagnostics.profitable_candidates = len(opportunities)

        return opportunities
