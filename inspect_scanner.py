from collections import Counter, defaultdict
from decimal import Decimal

from app.scanner.indodax_scanner import IndodaxScanner


def main():
    scanner = IndodaxScanner()

    try:
        candidates = scanner.scan_once()

        print(f"Total kandidat valid: {len(candidates)}")

        # Distribusi pasangan berdasarkan mata uang kuotasi.
        quote_counts = Counter(candidate.quote for candidate in candidates)

        print("\n=== PASANGAN PER QUOTE CURRENCY ===")
        for quote, count in sorted(quote_counts.items()):
            print(f"{quote:10} {count:4} pasangan")

        # Analisis spread.
        print("\n=== FILTER SPREAD ===")
        for threshold in (
            Decimal("0.10"),
            Decimal("0.25"),
            Decimal("0.50"),
            Decimal("1.00"),
            Decimal("2.00"),
        ):
            count = sum(
                candidate.spread_pct <= threshold
                for candidate in candidates
            )
            print(f"Spread <= {threshold}%: {count} pasangan")

        # Statistik volume per quote currency.
        volumes_by_quote = defaultdict(list)

        for candidate in candidates:
            volume = candidate.quote_volume
            if volume is not None and volume > 0:
                volumes_by_quote[candidate.quote].append(volume)

        print("\n=== DISTRIBUSI QUOTEVOLUME PER QUOTE ===")
        for quote in sorted(volumes_by_quote):
            volumes = sorted(volumes_by_quote[quote])
            count = len(volumes)

            median = volumes[count // 2]
            p75 = volumes[min(count - 1, int(count * 0.75))]
            p90 = volumes[min(count - 1, int(count * 0.90))]

            print(
                f"{quote:10} "
                f"jumlah={count:3} "
                f"min={volumes[0]} "
                f"median={median} "
                f"p75={p75} "
                f"p90={p90}"
            )

        # Contoh pasangan dengan spread terendah.
        print("\n=== 15 SPREAD TERENDAH ===")
        for candidate in sorted(
            candidates,
            key=lambda item: item.spread_pct,
        )[:15]:
            print(
                f"{candidate.symbol:15} "
                f"spread={candidate.spread_pct:.4f}% "
                f"quoteVolume={candidate.quote_volume}"
            )

    finally:
        scanner.close()


if __name__ == "__main__":
    main()