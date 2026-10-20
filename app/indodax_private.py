import hashlib
import hmac
import json
import os
import time
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=False)


class IndodaxPrivateClient:
    """Klien Indodax Trade API V2 untuk membaca saldo akun."""

    BASE_URL = "https://api.indodax.com"

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None
            else os.getenv("INDODAX_API_KEY", "")
        ).strip()

        self.api_secret = (
            api_secret if api_secret is not None
            else os.getenv("INDODAX_API_SECRET", "")
        ).strip()

        self.timeout = timeout

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "INDODAX_API_KEY dan INDODAX_API_SECRET "
                "wajib diisi di file .env."
            )

        if timeout <= 0:
            raise ValueError("Timeout harus lebih besar dari nol.")

    def _get_account(self) -> dict:
        """Memanggil endpoint akun V2 dengan autentikasi HMAC-SHA256."""
        params = {
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000,
        }

        query = urlencode(params)

        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        request = Request(
            f"{self.BASE_URL}/api/v2/account?{query}",
            headers={
                "X-APIKEY": self.api_key,
                "Sign": signature,
                "Accept": "application/json",
                "User-Agent": "CryptoTradingBot/1.0",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw_body = response.read().decode(
                    "utf-8", errors="replace"
                )

        except HTTPError as exc:
            raw_body = exc.read().decode(
                "utf-8", errors="replace"
            )

            try:
                error_payload = json.loads(raw_body)

                if isinstance(error_payload, dict):
                    code = error_payload.get(
                        "code",
                        error_payload.get("error_code", "unknown"),
                    )
                    message = error_payload.get(
                        "msg",
                        error_payload.get(
                            "message",
                            error_payload.get("error", raw_body[:500]),
                        ),
                    )
                    detail = f"kode={code}, pesan={message}"
                else:
                    detail = f"respons={raw_body[:500]!r}"

            except json.JSONDecodeError:
                detail = f"respons={raw_body[:500]!r}"

            raise RuntimeError(
                f"Indodax menolak permintaan akun: "
                f"HTTP {exc.code}, {detail}"
            ) from None

        except (URLError, TimeoutError, OSError):
            raise RuntimeError(
                "Tidak dapat terhubung ke API Indodax. "
                "Periksa koneksi internet atau coba kembali."
            ) from None

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            raise RuntimeError(
                "Respons API Indodax bukan JSON yang valid."
            ) from None

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Format respons akun Indodax tidak valid."
            )

        if "code" in payload and payload["code"] not in (0, "0", None):
            raise RuntimeError(
                f"Permintaan akun gagal: "
                f"{payload.get('msg', payload['code'])}"
            )

        if "balances" not in payload:
            raise RuntimeError(
                "Data balances tidak ditemukan pada respons akun. "
                "Periksa format respons Trade API V2."
            )

        return payload

    def get_balance_details(self) -> dict[str, dict[str, Decimal]]:
        """Mengembalikan saldo tersedia dan terkunci per aset."""
        account = self._get_account()
        raw_balances = account["balances"]

        if not isinstance(raw_balances, list):
            raise RuntimeError(
                "Format daftar saldo Indodax tidak valid."
            )

        balances: dict[str, dict[str, Decimal]] = {}

        for item in raw_balances:
            if not isinstance(item, dict):
                raise RuntimeError("Format item saldo tidak valid.")

            asset = item.get("asset")

            if not isinstance(asset, str) or not asset.strip():
                raise RuntimeError("Nama aset pada saldo tidak valid.")

            try:
                free = Decimal(str(item.get("free", "0")))
                locked = Decimal(str(item.get("locked", "0")))
            except (InvalidOperation, ValueError):
                raise RuntimeError(
                    f"Nilai saldo aset {asset} tidak valid."
                ) from None

            if (
                not free.is_finite()
                or not locked.is_finite()
                or free < 0
                or locked < 0
            ):
                raise RuntimeError(
                    f"Nilai saldo aset {asset} tidak valid."
                )

            balances[asset.lower()] = {
                "free": free,
                "locked": locked,
            }

        return balances

    def get_balances(self) -> dict[str, Decimal]:
        """Saldo tersedia nonzero, kompatibel dengan pemanggil lama."""
        return {
            asset: details["free"]
            for asset, details in self.get_balance_details().items()
            if details["free"] != 0
        }

    def check_connection(self) -> bool:
        """Memastikan endpoint akun dapat diakses."""
        self._get_account()
        return True
