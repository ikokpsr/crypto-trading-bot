
from app.scanner.profitability_scanner import ProfitabilityScanner


def main():
    evaluator = ProfitabilityScanner(max_order_books=20)
    scanner = evaluator.scanner

    try:
        print("=== PEMERIKSAAN PROFITABILITAS INDODAX ===")
        print("Mode                   : READ-ONLY")
        print(f"Nominal simulasi       : Rp{evaluator.order_budget:,.0f}")
        print(
            "Target profit bersih   : "
            f">= {evaluator.target_net_profit_pct}%"
        )
        print(f"Maksimal order book    : {evaluator.max_order_books}")
        print()

        results = evaluator.scan_once()
        stats = evaluator.last_diagnostics

        print("=== HASIL PEMINDAIAN ===")
        print(f"Kandidat awal          : {stats.candidates_found}")
        print(f"Order book dicoba      : {stats.order_books_attempted}")
        print(f"Request gagal          : {stats.order_books_failed}")
        print(f"Order book tidak valid : {stats.invalid_order_books}")
        print(f"Metadata tidak valid   : {stats.invalid_market_metadata}")
        print(f"Estimasi ditolak       : {stats.insufficient_depth}")
        print(f"Profit di bawah target : {stats.below_profit_target}")
        print(f"Kandidat lolos         : {stats.profitable_candidates}")

        if not results:
            print()
            print("Belum ada kandidat yang memenuhi target.")
            print(
                "Periksa statistik di atas untuk mengetahui "
                "tahap penyaringan yang paling banyak menggugurkan kandidat."
            )

        for item in results:
            print(f"\nPasangan        : {item.symbol}")
            print(f"Biaya beli      : Rp{item.buy_cost:,.2f}")
            print(f"Fee beli        : Rp{item.buy_fee:,.2f}")
            print(f"Hasil jual      : Rp{item.sell_proceeds:,.2f}")
            print(f"Fee jual        : Rp{item.sell_fee:,.2f}")
            print(f"Profit bersih   : Rp{item.net_profit:,.2f}")
            print(f"Profit bersih % : {item.net_profit_pct:.4f}%")

    finally:
        scanner.close()


if __name__ == "__main__":
    main()
