
from decimal import Decimal

import pytest

from app.scanner.execution_estimator import (
    DEFAULT_ORDER_BUDGET,
    TAKER_BUY_FEE,
    TAKER_SELL_FEE,
    estimate_round_trip,
    simulate_buy,
    simulate_sell,
)


D = Decimal


def test_simulate_buy_respects_budget_including_fee():
    asks = [[D("1000"), D("200")]]

    cost, fee, amount = simulate_buy(asks)

    assert cost + fee <= DEFAULT_ORDER_BUDGET
    assert amount > 0
    assert fee == cost * TAKER_BUY_FEE


def test_simulate_sell_accounts_for_taker_fee():
    bids = [[D("1100"), D("100")]]

    proceeds, fee, filled = simulate_sell(bids, D("10"))

    assert proceeds == D("11000")
    assert fee == proceeds * TAKER_SELL_FEE
    assert filled == D("10")


def test_round_trip_returns_net_profit_after_both_fees():
    asks = [[D("1000"), D("200")]]
    bids = [[D("990"), D("200")]]

    result = estimate_round_trip(asks, bids)

    assert result is not None
    assert result.buy_fee > 0
    assert result.sell_fee > 0
    assert result.net_profit == (
        result.sell_proceeds
        - result.sell_fee
        - result.buy_cost
        - result.buy_fee
    )
    assert result.net_profit_pct == (
        result.net_profit / DEFAULT_ORDER_BUDGET * D("100")
    )


def test_round_trip_rejects_insufficient_sell_depth():
    asks = [[D("1000"), D("200")]]
    bids = [[D("990"), D("1")]]

    assert estimate_round_trip(asks, bids) is None


def test_invalid_budget_is_rejected():
    with pytest.raises(ValueError):
        simulate_buy(
            [[D("1000"), D("10")]],
            budget=D("0"),
        )


def test_fee_constants_are_expected_rates():
    assert TAKER_BUY_FEE == D("0.0020555")
    assert TAKER_SELL_FEE == D("0.0041555")


def test_simulate_buy_rounds_amount_down_to_step():
    asks = [[D("1000"), D("100")]]

    _, _, amount = simulate_buy(
        asks,
        budget=D("100000"),
        amount_step=D("0.1"),
        min_amount=D("0.1"),
        min_cost=D("0"),
    )

    assert amount == amount.quantize(D("0.1"))
    assert amount * D("1000") <= D("100000")


def test_simulate_buy_rejects_amount_below_minimum():
    asks = [[D("1000"), D("0.01")]]

    cost, fee, amount = simulate_buy(
        asks,
        budget=D("100000"),
        amount_step=D("0.001"),
        min_amount=D("0.1"),
        min_cost=D("0"),
    )

    assert cost == D("0")
    assert fee == D("0")
    assert amount == D("0")


@pytest.mark.parametrize(
    "budget",
    [
        D("NaN"),
        D("Infinity"),
        D("-Infinity"),
    ],
)
def test_simulate_buy_rejects_non_finite_budget(budget):
    with pytest.raises(ValueError):
        simulate_buy(
            [[D("1000"), D("100")]],
            budget=budget,
        )


@pytest.mark.parametrize(
    "fee_rate",
    [
        D("NaN"),
        D("Infinity"),
        D("-Infinity"),
    ],
)
def test_simulate_buy_rejects_non_finite_fee(fee_rate):
    with pytest.raises(ValueError):
        simulate_buy(
            [[D("1000"), D("100")]],
            fee_rate=fee_rate,
        )


@pytest.mark.parametrize(
    "price, available",
    [
        (D("NaN"), D("10")),
        (D("Infinity"), D("10")),
        (D("1000"), D("NaN")),
        (D("1000"), D("Infinity")),
        (D("-1"), D("10")),
        (D("1000"), D("-1")),
    ],
)
def test_simulate_buy_ignores_invalid_order_book_levels(
    price, available
):
    cost, fee, amount = simulate_buy(
        [[price, available]],
        min_cost=D("0"),
    )

    assert cost == D("0")
    assert fee == D("0")
    assert amount == D("0")


@pytest.mark.parametrize(
    "price, available",
    [
        (D("NaN"), D("10")),
        (D("Infinity"), D("10")),
        (D("1000"), D("NaN")),
        (D("1000"), D("Infinity")),
        (D("-1"), D("10")),
        (D("1000"), D("-1")),
    ],
)
def test_simulate_sell_ignores_invalid_order_book_levels(
    price, available
):
    proceeds, fee, filled = simulate_sell(
        [[price, available]],
        amount=D("1"),
    )

    assert proceeds == D("0")
    assert fee == D("0")
    assert filled == D("0")


@pytest.mark.parametrize(
    "amount",
    [
        D("NaN"),
        D("Infinity"),
        D("-Infinity"),
        D("-1"),
    ],
)
def test_simulate_sell_rejects_invalid_amount(amount):
    with pytest.raises(ValueError):
        simulate_sell(
            [[D("1000"), D("10")]],
            amount=amount,
        )


@pytest.mark.parametrize(
    "fee_rate",
    [
        D("NaN"),
        D("Infinity"),
        D("-Infinity"),
        D("-0.1"),
    ],
)
def test_simulate_sell_rejects_invalid_fee(fee_rate):
    with pytest.raises(ValueError):
        simulate_sell(
            [[D("1000"), D("10")]],
            amount=D("1"),
            fee_rate=fee_rate,
        )


def test_simulate_sell_rejects_amount_not_aligned_to_step():
    with pytest.raises(ValueError, match="amount step"):
        simulate_sell(
            [[D("1000"), D("10")]],
            amount=D("1.05"),
            amount_step=D("0.1"),
        )


def test_simulate_sell_accepts_amount_aligned_to_step():
    proceeds, fee, filled = simulate_sell(
        [[D("1000"), D("10")]],
        amount=D("1.2"),
        amount_step=D("0.1"),
    )

    assert proceeds == D("1200")
    assert fee == D("1200") * TAKER_SELL_FEE
    assert filled == D("1.2")


@pytest.mark.parametrize(
    "asks",
    [
        [[D("101"), D("10")], [D("100"), D("10")]],
    ],
)
def test_simulate_buy_rejects_unsorted_asks(asks):
    with pytest.raises(ValueError):
        simulate_buy(asks)


@pytest.mark.parametrize(
    "bids",
    [
        [[D("100"), D("10")], [D("101"), D("10")]],
    ],
)
def test_simulate_sell_rejects_unsorted_bids(bids):
    with pytest.raises(ValueError):
        simulate_sell(bids, amount=D("1"))


@pytest.mark.parametrize(
    "asks, bids",
    [
        (
            [[D("100"), D("10")]],
            [[D("101"), D("10")]],
        ),
    ],
)
def test_round_trip_rejects_crossed_order_book(asks, bids):
    with pytest.raises(ValueError):
        estimate_round_trip(
            asks,
            bids,
            min_cost=D("0"),
        )


def test_round_trip_rejects_sell_value_below_minimum_cost():
    asks = [[D("1000"), D("200")]]
    bids = [[D("100"), D("200")]]

    result = estimate_round_trip(
        asks,
        bids,
        budget=D("100000"),
        amount_step=D("0.00000001"),
        min_amount=D("0"),
        min_cost=D("25000"),
    )

    assert result is None


def test_round_trip_accepts_sell_value_at_minimum_cost():
    asks = [[D("1000"), D("200")]]
    bids = [[D("1000"), D("200")]]

    result = estimate_round_trip(
        asks,
        bids,
        budget=D("100000"),
        amount_step=D("0.00000001"),
        min_amount=D("0"),
        min_cost=D("25000"),
    )

    assert result is not None
    assert result.sell_proceeds >= D("25000")
