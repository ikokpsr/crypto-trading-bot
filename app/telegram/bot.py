import json
import logging
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import ccxt

from app.config import load_settings
from app.indodax_private import IndodaxPrivateClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("crypto_bot.telegram")


class TelegramBot:
    """Telegram polling bot dengan akses baca saja."""

    def __init__(self) -> None:
        self.settings = load_settings()
        self.token = self.settings.telegram_bot_token
        self.allowed_user_ids = set(
            self.settings.telegram_allowed_user_ids
        )
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset: int | None = None

        if not self.token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN belum diisi di file .env."
            )

        if not self.allowed_user_ids:
            raise ValueError(
                "TELEGRAM_ALLOWED_USER_IDS masih kosong. "
                "Isi dengan Telegram user ID milik Anda."
            )

    def _api(
        self,
        method: str,
        data: dict | None = None,
    ) -> dict:
        url = f"{self.base_url}/{method}"
        body = None

        if data is not None:
            body = json.dumps(data).encode("utf-8")

        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST" if body is not None else "GET",
        )

        try:
            with urlopen(request, timeout=35) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )
        except HTTPError as exc:
            # Jangan mencetak URL karena URL memuat token bot.
            raise RuntimeError(
                f"Telegram API mengembalikan HTTP {exc.code}."
            ) from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError(
                "Tidak dapat terhubung ke Telegram API."
            ) from None
        except json.JSONDecodeError:
            raise RuntimeError(
                "Respons Telegram bukan JSON yang valid."
            ) from None

        if not isinstance(result, dict) or not result.get("ok"):
            description = (
                result.get("description", "Respons tidak valid.")
                if isinstance(result, dict)
                else "Respons tidak valid."
            )
            raise RuntimeError(f"Telegram API gagal: {description}")

        return result

    def send_message(self, chat_id: int, text: str) -> None:
        # Tidak memakai parse_mode agar teks tidak ditafsirkan sebagai HTML.
        self._api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text[:4000],
            },
        )

    @staticmethod
    def help_text() -> str:
        return (
            "Perintah Crypto Trading Bot\n\n"
            "/status - Status bot dan koneksi Indodax\n"
            "/saldo - Baca saldo akun Indodax\n"
            "/market [PAIR] - Harga pasar, default BTC/IDR\n"
            "/paper - Status mode Paper Trading\n"
            "/help - Daftar perintah\n\n"
            "Bot ini hanya menyediakan informasi. "
            "Tidak ada perintah order real."
        )

    def command_status(self) -> str:
        try:
            IndodaxPrivateClient().check_connection()
            account_status = "TERHUBUNG"
        except (ValueError, RuntimeError) as exc:
            account_status = f"GAGAL ({exc})"

        return (
            "Status Crypto Trading Bot\n\n"
            f"Mode trading: {self.settings.trading_mode}\n"
            f"Exchange: {self.settings.exchange_id}\n"
            f"Indodax private API: {account_status}\n"
            "Eksekusi order real: NONAKTIF"
        )

    def command_balance(self) -> str:
        balances = IndodaxPrivateClient().get_balance_details()
        nonzero = {
            asset: values
            for asset, values in balances.items()
            if values["free"] != 0 or values["locked"] != 0
        }

        if not nonzero:
            return "Saldo akun terbaca, tetapi semua saldo aset bernilai nol."

        lines = ["Saldo Indodax (baca saja):"]

        for asset, values in sorted(nonzero.items()):
            lines.append(
                f"{asset.upper()}: tersedia "
                f"{values['free']:.12f}, terkunci "
                f"{values['locked']:.12f}"
            )

        lines.append("\nTidak ada order yang dikirim.")
        return "\n".join(lines)

    def command_market(self, symbol: str) -> str:
        exchange = None

        try:
            exchange_class = getattr(ccxt, self.settings.exchange_id)
            exchange = exchange_class({"enableRateLimit": True})
            markets = exchange.load_markets()

            if symbol not in markets:
                return (
                    f"Pair {symbol} tidak ditemukan di "
                    f"{self.settings.exchange_id}. "
                    "Contoh: /market BTC/IDR"
                )

            ticker = exchange.fetch_ticker(symbol)
            last = ticker.get("last")
            bid = ticker.get("bid")
            ask = ticker.get("ask")
            quote_volume = ticker.get("quoteVolume")

            def fmt(value) -> str:
                if value is None:
                    return "-"
                return f"{Decimal(str(value)):,.8f}"

            return (
                f"Market: {symbol}\n"
                f"Harga terakhir: {fmt(last)}\n"
                f"Bid: {fmt(bid)}\n"
                f"Ask: {fmt(ask)}\n"
                f"Volume quote 24 jam: {fmt(quote_volume)}\n"
                "Sumber: data pasar publik; bukan sinyal beli/jual."
            )
        except (ccxt.BaseError, AttributeError, ValueError) as exc:
            logger.warning("Gagal mengambil market: %s", type(exc).__name__)
            return (
                f"Gagal mengambil data {symbol}. "
                "Pastikan pair tersedia dan coba lagi."
            )
        finally:
            if exchange is not None:
                try:
                    exchange.close()
                except Exception:
                    pass

    def handle_update(self, update: dict) -> None:
        message = update.get("message")
        if not isinstance(message, dict):
            return

        sender = message.get("from") or {}
        chat = message.get("chat") or {}
        user_id = sender.get("id")
        chat_id = chat.get("id")
        text = message.get("text", "")

        if not isinstance(user_id, int) or not isinstance(chat_id, int):
            return
        if not isinstance(text, str) or not text.startswith("/"):
            return

        # Tolak semua user yang tidak terdaftar.
        if user_id not in self.allowed_user_ids:
            logger.warning("Perintah ditolak untuk user ID yang tidak diizinkan.")
            self.send_message(
                chat_id,
                "Akses ditolak. Hubungi administrator bot.",
            )
            return

        parts = text.strip().split()
        command = parts[0].split("@", 1)[0].lower()
        args = parts[1:]

        try:
            if command in ("/start", "/help"):
                reply = self.help_text()
            elif command == "/status":
                reply = self.command_status()
            elif command == "/saldo":
                reply = self.command_balance()
            elif command == "/paper":
                reply = (
                    f"Mode saat ini: {self.settings.trading_mode}\n"
                    "Paper Trading adalah simulasi, bukan order real.\n"
                    "Eksekusi order real melalui bot: NONAKTIF."
                )
            elif command == "/market":
                symbol = args[0].upper() if args else "BTC/IDR"
                reply = self.command_market(symbol)
            else:
                reply = "Perintah tidak dikenal.\n\n" + self.help_text()

        except (RuntimeError, ValueError) as exc:
            logger.warning(
                "Perintah %s gagal: %s",
                command,
                type(exc).__name__,
            )
            reply = "Permintaan gagal. Periksa koneksi dan konfigurasi bot."

        self.send_message(chat_id, reply)

    def run(self) -> None:
        me = self._api("getMe")["result"]
        logger.info("Bot Telegram aktif sebagai @%s", me.get("username"))
        logger.info("Mode trading: %s", self.settings.trading_mode)
        logger.info("Polling berjalan. Tekan Ctrl+C untuk berhenti.")

        while True:
            try:
                params = {"timeout": 25}
                if self.offset is not None:
                    params["offset"] = self.offset

                query = urlencode(params)
                result = self._api("getUpdates?" + query)

                for update in result.get("result", []):
                    self.offset = update["update_id"] + 1
                    try:
                        self.handle_update(update)
                    except Exception:
                        # Hindari mencetak isi pesan, token, atau saldo ke log.
                        logger.exception("Gagal memproses update Telegram.")

            except KeyboardInterrupt:
                logger.info("Bot dihentikan oleh pengguna.")
                break
            except Exception as exc:
                logger.warning(
                    "Polling gagal (%s). Mencoba kembali dalam 5 detik.",
                    type(exc).__name__,
                )
                time.sleep(5)


def main() -> None:
    TelegramBot().run()


if __name__ == "__main__":
    main()
