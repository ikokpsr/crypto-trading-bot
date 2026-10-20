
from dataclasses import dataclass
from decimal import Decimal, DecimalException, ROUND_DOWN


TAKER_BUY_FEE = Decimal("0.0020555")
TAKER_SELL_FEE = Decimal("0.0041555")

DEFAULT_ORDER_BUDGET = Decimal("100000")
DEFAULT_MIN_ORDER_COST = Decimal("25000")
TARGET_NET_PROFIT_PCT = Decimal("0.5")


@dataclass(frozen=True)
class ExecutionEstimate:
    buy_cost: Decimal
    buy_fee: Decimal
    base_amount: Decimal
    sell_proceeds: Decimal
    sell_fee: Decimal
    net_profit: Decimal
    net_profit_pct: Decimal


def _require_decimal(
    value: Decimal,
    name: str,
    *,
    allow_zero: bool = True,
) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValueError(f"{name} harus berupa Decimal.")

    if not value.is_finite():
        raise ValueError(f"{name} harus berupa angka finite.")

    if value < 0 or (not allow_zero and value == 0):
        raise ValueError(f"{name} memiliki nilai yang tidak valid.")

    return value


def _floor_to_step(amount: Decimal, step: Decimal) -> Decimal:
    if not step.is_finite() or step <= 0:
        raise ValueError("Amount step harus positif dan finite.")

    steps = (amount / step).to_integral_value(rounding=ROUND_DOWN)
    return steps * step


def _valid_order_book_level(level) -> bool:
    if not isinstance(level, (list, tuple)) or len(level) < 2:
        return False

    price, available = level[0], level[1]

    if not isinstance(price, Decimal):
        return False

    if not isinstance(available, Decimal):
        return False

    return (
        price.is_finite()
        and available.is_finite()
        and price > 0
        and available > 0
    )


def _validate_order_book_order(levels, *, is_asks: bool) -> None:
    previous_price = None

    for level in levels:
        if not _valid_order_book_level(level):
            continue

        price = level[0]

        if previous_price is not None:
            if is_asks and price < previous_price:
                raise ValueError(
                    "Ask levels harus berurutan dari harga terendah."
                )

            if not is_asks and price > previous_price:
                raise ValueError(
                    "Bid levels harus berurutan dari harga tertinggi."
                )

        previous_price = price


def _valid_levels(levels):
    return [
        level
        for level in levels
        if _valid_order_book_level(level)
    ]


def simulate_buy(
    asks,
    budget=DEFAULT_ORDER_BUDGET,
    fee_rate=TAKER_BUY_FEE,
    amount_step=Decimal("0.00000001"),
    min_amount=Decimal("0"),
    min_cost=DEFAULT_MIN_ORDER_COST,
):
    budget = _require_decimal(
        budget, "Budget", allow_zero=False
    )
    fee_rate = _require_decimal(fee_rate, "Buy fee")
    amount_step = _require_decimal(
        amount_step, "Amount step", allow_zero=False
    )
    min_amount = _require_decimal(min_amount, "Minimum amount")
    min_cost = _require_decimal(min_cost, "Minimum cost")

    if fee_rate >= 1:
        raise ValueError("Buy fee harus kurang dari 1.")

    _validate_order_book_order(asks, is_asks=True)
    valid_asks = _valid_levels(asks)

    if not valid_asks:
        return Decimal("0"), Decimal("0"), Decimal("0")

    remaining_budget = budget
    total_cost = Decimal("0")
    total_fee = Decimal("0")
    total_amount = Decimal("0")

    for price, available in valid_asks:
        if remaining_budget <= 0:
            break

        # Budget mencakup biaya pembelian dan fee.
        affordable_amount = remaining_budget / (
            price * (Decimal("1") + fee_rate)
        )
        amount = min(available, affordable_amount)

        if amount <= 0:
            continue

        total_amount += amount
        level_cost = amount * price
        level_fee = level_cost * fee_rate

        total_cost += level_cost
        total_fee += level_fee
        remaining_budget -= level_cost + level_fee

    total_amount = _floor_to_step(total_amount, amount_step)

    if total_amount <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")

    # Hitung ulang biaya atas jumlah yang telah dibulatkan.
    remaining_amount = total_amount
    total_cost = Decimal("0")

    for price, available in valid_asks:
        if remaining_amount <= 0:
            break

        filled = min(available, remaining_amount)
        total_cost += filled * price
        remaining_amount -= filled

    if remaining_amount > 0:
        return Decimal("0"), Decimal("0"), Decimal("0")

    total_fee = total_cost * fee_rate

    if total_cost + total_fee > budget:
        return Decimal("0"), Decimal("0"), Decimal("0")

    if total_amount < min_amount or total_cost < min_cost:
        return Decimal("0"), Decimal("0"), Decimal("0")

    return total_cost, total_fee, total_amount


def simulate_sell(
    bids,
    amount,
    fee_rate=TAKER_SELL_FEE,
    amount_step=None,
):
    amount = _require_decimal(
        amount, "Amount", allow_zero=False
    )
    fee_rate = _require_decimal(fee_rate, "Sell fee")

    if fee_rate >= 1:
        raise ValueError("Sell fee harus kurang dari 1.")

    if amount_step is not None:
        amount_step = _require_decimal(
            amount_step, "Amount step", allow_zero=False
        )

        if _floor_to_step(amount, amount_step) != amount:
            raise ValueError(
                "Amount harus sesuai dengan kelipatan amount step."
            )

    _validate_order_book_order(bids, is_asks=False)
    valid_bids = _valid_levels(bids)

    remaining_amount = amount
    total_proceeds = Decimal("0")
    filled_amount = Decimal("0")

    for price, available in valid_bids:
        if remaining_amount <= 0:
            break

        filled = min(available, remaining_amount)
        total_proceeds += filled * price
        filled_amount += filled
        remaining_amount -= filled

    total_fee = total_proceeds * fee_rate

    return total_proceeds, total_fee, filled_amount


def estimate_round_trip(
    asks,
    bids,
    budget=DEFAULT_ORDER_BUDGET,
    amount_step=Decimal("0.00000001"),
    min_amount=Decimal("0"),
    min_cost=DEFAULT_MIN_ORDER_COST,
):
    budget = _require_decimal(
        budget, "Budget", allow_zero=False
    )
    amount_step = _require_decimal(
        amount_step, "Amount step", allow_zero=False
    )
    min_amount = _require_decimal(min_amount, "Minimum amount")
    min_cost = _require_decimal(min_cost, "Minimum cost")

    _validate_order_book_order(asks, is_asks=True)
    _validate_order_book_order(bids, is_asks=False)

    valid_asks = _valid_levels(asks)
    valid_bids = _valid_levels(bids)

    if not valid_asks or not valid_bids:
        return None

    best_ask = valid_asks[0][0]
    best_bid = valid_bids[0][0]

    if best_bid > best_ask:
        raise ValueError("Crossed order book: best bid melebihi best ask.")

    buy_cost, buy_fee, amount = simulate_buy(
        asks=valid_asks,
        budget=budget,
        amount_step=amount_step,
        min_amount=min_amount,
        min_cost=min_cost,
    )

    if amount <= 0:
        return None

    sell_proceeds, sell_fee, sold_amount = simulate_sell(
        bids=valid_bids,
        amount=amount,
        amount_step=amount_step,
    )

    # Seluruh jumlah hasil beli harus bisa dijual.
    if sold_amount != amount:
        return None

    # Validasi batas minimum transaksi jual.
    if sold_amount < min_amount:
        return None

    if sell_proceeds < min_cost:
        return None

    net_profit = (
        sell_proceeds
        - sell_fee
        - buy_cost
        - buy_fee
    )

    net_profit_pct = (net_profit / budget) * Decimal("100")

    return ExecutionEstimate(
        buy_cost=buy_cost,
        buy_fee=buy_fee,
        base_amount=amount,
        sell_proceeds=sell_proceeds,
        sell_fee=sell_fee,
        net_profit=net_profit,
        net_profit_pct=net_profit_pct,
    )
