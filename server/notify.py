"""Gửi thông báo Telegram cho admin (vd. khi CTV gửi phiếu đổi ca).

Cấu hình (repo public → KHÔNG ghi token vào code):
  - Token bot: biến môi trường TELEGRAM_BOT_TOKEN hoặc settings.telegram_bot_token
  - Chat nhận: biến môi trường TELEGRAM_CHAT_ID hoặc settings.telegram_chat_id (nhiều id, cách nhau dấu phẩy)
Nếu chưa có chat id: nhắn /start cho bot, lần gửi kế tiếp sẽ tự lấy chat id từ getUpdates và lưu lại.
Nút Duyệt/Từ chối trong tin nhắn → Telegram gọi webhook /api/telegram/webhook (tự đăng ký khi server khởi động).
Gửi chạy ở luồng nền, lỗi chỉ in log — không bao giờ làm hỏng request của CTV.
"""
import hashlib
import json
import os
import threading
import urllib.parse
import urllib.request

from . import db

API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API.format(token=token, method=method), data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def _config(con) -> tuple[str, list[str]]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or db.get_setting(con, "telegram_bot_token", "").strip()
    chats = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or db.get_setting(con, "telegram_chat_id", "").strip()
    return token, [c.strip() for c in chats.split(",") if c.strip()]


def _discover_chats(con, token: str) -> list[str]:
    """Lấy chat id của những người đã nhắn riêng cho bot, rồi lưu vào settings."""
    res = _call(token, "getUpdates", {"allowed_updates": json.dumps(["message"])})
    ids = []
    for upd in res.get("result", []):
        chat = (upd.get("message") or {}).get("chat") or {}
        if chat.get("type") == "private" and str(chat.get("id")) not in ids:
            ids.append(str(chat["id"]))
    if ids:
        db.set_setting(con, "telegram_chat_id", ",".join(ids))
        con.commit()
    return ids


PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://cong-ctv.onrender.com").rstrip("/")


def config(con) -> tuple[str, list[str]]:
    return _config(con)


def webhook_secret(token: str) -> str:
    return hashlib.sha256(("ctv-webhook:" + token).encode()).hexdigest()[:48]


def call(con, method: str, params: dict) -> dict | None:
    """Gọi Bot API đồng bộ; lỗi chỉ in log."""
    token, _ = _config(con)
    if not token:
        return None
    try:
        return _call(token, method, params)
    except Exception as e:  # noqa: BLE001
        print(f"[notify] Lỗi Telegram {method}: {e}")
        return None


def _send(text: str, buttons: list | None):
    con = db.connect()
    try:
        token, chats = _config(con)
        if not token:
            return
        if not chats:
            chats = _discover_chats(con, token)
            if not chats:
                print("[notify] Chưa có chat id Telegram — hãy nhắn /start cho bot")
                return
        params = {"text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"}
        if buttons:
            params["reply_markup"] = json.dumps({"inline_keyboard": buttons})
        for chat in chats:
            _call(token, "sendMessage", {"chat_id": chat, **params})
    except Exception as e:  # noqa: BLE001 — thông báo là phụ, không được làm hỏng luồng chính
        print(f"[notify] Lỗi gửi Telegram: {e}")
    finally:
        con.close()


def send_async(text: str, buttons: list | None = None):
    threading.Thread(target=_send, args=(text, buttons), daemon=True).start()


def _ensure_webhook():
    con = db.connect()
    try:
        token, _ = _config(con)
        if not token:
            return
        url = PUBLIC_URL + "/api/telegram/webhook"
        info = _call(token, "getWebhookInfo", {}).get("result", {})
        if info.get("url") != url:
            _call(token, "setWebhook", {"url": url, "secret_token": webhook_secret(token),
                                        "allowed_updates": json.dumps(["callback_query", "message"])})
            print(f"[notify] Đã đăng ký webhook Telegram: {url}")
    except Exception as e:  # noqa: BLE001
        print(f"[notify] Lỗi đăng ký webhook: {e}")
    finally:
        con.close()


def ensure_webhook_async():
    threading.Thread(target=_ensure_webhook, daemon=True).start()


def esc(s) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
