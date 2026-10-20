
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    FILLED = "filled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PaperConfig:
    initial_balance_idr: Decimal = Decimal("1000000")
    fee_rate: Decimal = Decimal("0.002")

    
    def __post_init__(self) -> None:
        if not isinstance(self.initial_balance_idr, Decimal):
            raise ValueError("Saldo awal harus bertipe Decimal.")

        if not self.initial_balance_idr.is_finite():
            raise ValueError("Saldo awal harus berupa angka finite.")

        if self.initial_balance_idr <= 0:
            raise ValueError("Saldo awal harus lebih besar dari nol.")

        if not isinstance(self.fee_rate, Decimal):
            raise ValueError("Fee harus bertipe Decimal.")

        if not self.fee_rate.is_finite():
            raise ValueError("Fee harus berupa angka finite.")

        if not Decimal("0") <= self.fee_rate < Decimal("1"):
            raise ValueError("Fee harus berada dalam rentang 0 sampai kurang dari 1.")

@dataclass(frozen=True)
class PaperPosition:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    entry_fee_idr: Decimal

    
    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("Symbol tidak boleh kosong.")

        if not isinstance(self.quantity, Decimal):
            raise ValueError("Quantity posisi harus bertipe Decimal.")

        if not self.quantity.is_finite() or self.quantity <= 0:
            raise ValueError(
                "Quantity posisi harus berupa angka finite lebih besar dari nol."
            )

        if not isinstance(self.average_entry_price, Decimal):
            raise ValueError("Harga entry harus bertipe Decimal.")

        if (
            not self.average_entry_price.is_finite()
            or self.average_entry_price <= 0
        ):
            raise ValueError(
                "Harga entry harus berupa angka finite lebih besar dari nol."
            )

        if not isinstance(self.entry_fee_idr, Decimal):
            raise ValueError("Fee entry harus bertipe Decimal.")

        if (
            not self.entry_fee_idr.is_finite()
            or self.entry_fee_idr < 0
        ):
            raise ValueError(
                "Fee entry harus berupa angka finite dan tidak boleh negatif."
            )

@dataclass(frozen=True)
class PaperTrade:
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    fee_idr: Decimal
    timestamp_ms: int
    status: OrderStatus
    reason: str | None = None

    
    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("Symbol tidak boleh kosong.")

        if not isinstance(self.side, OrderSide):
            raise ValueError("Side transaksi tidak valid.")

        if not isinstance(self.quantity, Decimal):
            raise ValueError("Quantity transaksi harus bertipe Decimal.")
        if not self.quantity.is_finite() or self.quantity <= 0:
            raise ValueError("Quantity transaksi harus lebih besar dari nol.")

        if not isinstance(self.price, Decimal):
            raise ValueError("Harga transaksi harus bertipe Decimal.")
        if not self.price.is_finite() or self.price <= 0:
            raise ValueError("Harga transaksi harus lebih besar dari nol.")

        if not isinstance(self.fee_idr, Decimal):
            raise ValueError("Fee transaksi harus bertipe Decimal.")
        if not self.fee_idr.is_finite() or self.fee_idr < 0:
            raise ValueError("Fee transaksi tidak boleh negatif.")

        if isinstance(self.timestamp_ms, bool) or not isinstance(self.timestamp_ms, int):
            raise ValueError("Timestamp transaksi harus berupa bilangan bulat.")
        if self.timestamp_ms <= 0:
            raise ValueError("Timestamp transaksi harus positif.")

        if not isinstance(self.status, OrderStatus):
            raise ValueError("Status transaksi tidak valid.")

        if self.reason is not None and not isinstance(self.reason, str):
            raise ValueError("Reason harus berupa string atau None.")

        if self.status == OrderStatus.REJECTED:
            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "Transaksi yang ditolak harus memiliki alasan penolakan."
                )

        if self.status == OrderStatus.FILLED and self.reason is not None:
            raise ValueError(
                "Transaksi berhasil tidak boleh memiliki alasan penolakan."
            )

