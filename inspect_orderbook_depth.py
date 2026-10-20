from decimal import Decimal

from app.scanner.indodax_scanner import IndodaxScanner


def depth_within(levels, price_limit, *, is_ask):
    total_quote = Decimal("0")

    for level in levels:
        if len(level) < 2:
            continue

        price = Decimal(str(level[0]))
        amount = Decimal(str(level[1]))

        if price <= 0 or amount <= 0:
            continue

        if is_ask and price > price_limit:
            continue

        if not is_ask and price < price_limit:
            continue

        total_quote += price * amount

    return total_quote


def main():
    scanner = IndodaxScanner()

    try:
        candidates = scanner.scan_once()

        idr_candidates = [
            candidate
            for candidate in candidates
            if candidate.quote == "IDR"
        ]

        selected = sorted(
            idr_candidates,
            key=lambda candidate: candidate.spread_pct,
        )[:15]

        print(f"Pasangan yang diperiksa: {len(selected)}")
        print("Kedalaman dihitung dalam IDR, dalam jarak 0,5% dari best bid/ask.\n")

        for candidate in selected:
            try:
                orderbook = scanner.exchange.fetch_order_book(
                    candidate.symbol,
                    limit=20,
                )

                bids = orderbook.get("bids") or []
                asks = orderbook.get("asks") or []

                if not bids or not asks:
                    print(f"{candidate.symbol:15} ORDER BOOK KOSONG")
                    continue

                best_bid = Decimal(str(bids[0][0]))
                best_ask = Decimal(str(asks[0][0]))

                bid_limit = best_bid * Decimal("0.995")
                ask_limit = best_ask * Decimal("1.005")

                bid_depth = depth_within(
                    bids,
                    bid_limit,
                    is_ask=False,
                )
                ask_depth = depth_within(
                    asks,
                    ask_limit,
                    is_ask=True,
                )

                print(
                    f"{candidate.symbol:15} "
                    f"spread={candidate.spread_pct:.4f}% "
                    f"bid_depth={bid_depth:.0f} IDR "
                    f"ask_depth={ask_depth:.0f} IDR"
                )

            except Exception as exc:
                print(
                    f"{candidate.symbol:15} "
                    f"ERROR {type(exc).__name__}: {exc}"
                )

    finally:
        scanner.close()


if __name__ == "__main__":
    main()