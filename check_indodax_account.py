
from app.indodax_private import IndodaxPrivateClient


def main() -> int:
    try:
        client = IndodaxPrivateClient()
        balances = client.get_balances()

    except (ValueError, RuntimeError) as exc:
        print(f"Koneksi gagal: {exc}")
        return 1

    print("Koneksi API privat Indodax: BERHASIL")
    print(f"Jumlah aset dengan saldo tersedia: {len(balances)}")
    print("Daftar aset:", ", ".join(sorted(balances)) or "(kosong)")
    print("Mode: BACA SALDO SAJA")
    print("Order dikirim: TIDAK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
