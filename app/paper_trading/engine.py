from decimal import Decimal, DecimalException

from app.paper_trading.models import (
    OrderSide,
    OrderStatus,
    PaperConfig,
    PaperPosition,
    PaperTrade,
)


class PaperTradingEngine:
    def __init__(self, config: PaperConfig | None = None) -> None:
        self.config = config or PaperConfig()
        self.cash_balance_idr = self.config.initial_balance_idr
        self.positions: dict[str, PaperPosition] = {}
        self.trades: list[PaperTrade] = []
        self.realized_pnl_idr = Decimal("0")

    @staticmethod
    def _validate_order(
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        timestamp_ms: int,
    ) -> None:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Symbol tidak boleh kosong.")

        if not isinstance(quantity, Decimal):
            raise ValueError("Quantity harus bertipe Decimal.")
        if not quantity.is_finite() or quantity <= 0:
            raise ValueError("Quantity harus berupa angka finite lebih besar dari nol.")

        if not isinstance(price, Decimal):
            raise ValueError("Harga harus bertipe Decimal.")
        if not price.is_finite() or price <= 0:
            raise ValueError("Harga harus berupa angka finite lebih besar dari nol.")

        if isinstance(timestamp_ms, bool) or not isinstance(timestamp_ms, int):
            raise ValueError("Timestamp harus berupa bilangan bulat.")
        if timestamp_ms <= 0:
            raise ValueError("Timestamp harus positif.")

    @staticmethod
    def _validate_finite_results(**values: Decimal) -> None:
        for name, value in values.items():
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError(
                    f"Hasil perhitungan {name} tidak finite."
                )

    def _record_trade(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        timestamp_ms: int,
        status: OrderStatus,
        reason: str | None = None,
    ) -> PaperTrade:
        trade = PaperTrade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            fee_idr=fee,
            timestamp_ms=timestamp_ms,
            status=status,
            reason=reason,
        )
        self.trades.append(trade)
        return trade

    def buy(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        timestamp_ms: int,
    ) -> PaperTrade:
        self._validate_order(symbol, quantity, price, timestamp_ms)

        
        try:
            gross_cost = quantity * price
            fee = gross_cost * self.config.fee_rate
            total_cost = gross_cost + fee

            self._validate_finite_results(
                gross_cost=gross_cost,
                fee=fee,
                total_cost=total_cost,
            )
        except DecimalException as exc:
            raise ValueError(
                "Perhitungan biaya pembelian berada di luar rentang yang didukung."
            ) from exc

        self._validate_finite_results(
            cash_balance_idr=self.cash_balance_idr,
        )

        if total_cost > self.cash_balance_idr:
            return self._record_trade(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                price=price,
                fee=Decimal("0"),
                timestamp_ms=timestamp_ms,
                status=OrderStatus.REJECTED,
                reason="Saldo IDR tidak mencukupi termasuk fee.",
            )

        existing = self.positions.get(symbol)

        try:
            if existing is None:
                new_position = PaperPosition(
                    symbol=symbol,
                    quantity=quantity,
                    average_entry_price=price,
                    entry_fee_idr=fee,
                )
            else:
                new_quantity = existing.quantity + quantity

                weighted_cost = (
                    existing.quantity * existing.average_entry_price
                    + quantity * price
                )
                average_entry_price = weighted_cost / new_quantity
                new_entry_fee = existing.entry_fee_idr + fee

                self._validate_finite_results(
                    new_quantity=new_quantity,
                    weighted_cost=weighted_cost,
                    average_entry_price=average_entry_price,
                    new_entry_fee=new_entry_fee,
                )

                new_position = PaperPosition(
                    symbol=symbol,
                    quantity=new_quantity,
                    average_entry_price=average_entry_price,
                    entry_fee_idr=new_entry_fee,
                )
                
        except DecimalException as exc:
            raise ValueError(
                "Perhitungan posisi pembelian berada di luar rentang yang didukung."
            ) from exc

        
        try:
            new_balance = self.cash_balance_idr - total_cost

            self._validate_finite_results(
                new_balance=new_balance,
            )
        except DecimalException as exc:
            raise ValueError(
                "Perhitungan saldo setelah pembelian berada di luar rentang yang didukung."
            ) from exc

        trade = self._record_trade(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            price=price,
            fee=fee,
            timestamp_ms=timestamp_ms,
            status=OrderStatus.FILLED,
        )

        self.cash_balance_idr = new_balance
        self.positions[symbol] = new_position

        return trade


    def sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        timestamp_ms: int,
    ) -> PaperTrade:
        self._validate_order(symbol, quantity, price, timestamp_ms)

        position = self.positions.get(symbol)

        if position is None:
            return self._record_trade(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                price=price,
                fee=Decimal("0"),
                timestamp_ms=timestamp_ms,
                status=OrderStatus.REJECTED,
                reason="Tidak ada posisi untuk market ini.",
            )

        if quantity > position.quantity:
            return self._record_trade(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                price=price,
                fee=Decimal("0"),
                timestamp_ms=timestamp_ms,
                status=OrderStatus.REJECTED,
                reason="Jumlah jual melebihi posisi yang dimiliki.",
            )

        
        try:
            self._validate_finite_results(
                cash_balance_idr=self.cash_balance_idr,
                realized_pnl_idr=self.realized_pnl_idr,
            )

            gross_proceeds = quantity * price
            fee = gross_proceeds * self.config.fee_rate
            net_proceeds = gross_proceeds - fee

            entry_fee_allocated = (
                position.entry_fee_idr * quantity / position.quantity
            )
            entry_cost = quantity * position.average_entry_price
            realized_pnl = (
                net_proceeds - entry_cost - entry_fee_allocated
            )

            remaining_quantity = position.quantity - quantity
            remaining_entry_fee = (
                position.entry_fee_idr - entry_fee_allocated
            )
            new_balance = self.cash_balance_idr + net_proceeds
            new_realized_pnl = self.realized_pnl_idr + realized_pnl

            self._validate_finite_results(
                gross_proceeds=gross_proceeds,
                fee=fee,
                net_proceeds=net_proceeds,
                entry_fee_allocated=entry_fee_allocated,
                entry_cost=entry_cost,
                realized_pnl=realized_pnl,
                remaining_quantity=remaining_quantity,
                remaining_entry_fee=remaining_entry_fee,
                new_balance=new_balance,
                new_realized_pnl=new_realized_pnl,
            )

            if remaining_quantity < 0:
                raise ValueError(
                    "Sisa quantity posisi tidak boleh negatif."
                )

            if remaining_entry_fee < 0:
                raise ValueError(
                    "Sisa fee entry posisi tidak boleh negatif."
                )
        except DecimalException as exc:
            raise ValueError(
                "Perhitungan hasil penjualan berada di luar rentang yang didukung."
            ) from exc

        # Siapkan posisi baru sebelum mengubah state engine.
        new_position = None
        if remaining_quantity > 0:
            new_position = PaperPosition(
                symbol=symbol,
                quantity=remaining_quantity,
                average_entry_price=position.average_entry_price,
                entry_fee_idr=remaining_entry_fee,
            )

        # Catat transaksi sebelum melakukan commit state.
        trade = self._record_trade(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            price=price,
            fee=fee,
            timestamp_ms=timestamp_ms,
            status=OrderStatus.FILLED,
        )

        # Commit state setelah persiapan dan pencatatan berhasil.
        self.cash_balance_idr = new_balance
        self.realized_pnl_idr = new_realized_pnl

        if new_position is None:
            del self.positions[symbol]
        else:
            self.positions[symbol] = new_position

        return trade


