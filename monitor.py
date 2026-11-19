import json
import os
import re
import urllib.request

URLS = [
    "https://daesung.bstage.in/shop/products/49",
    "https://daesung.bstage.in/shop/products/59",
    "https://daesung.bstage.in/shop/products/60",
    "https://daesung.bstage.in/shop/products/61",
    "https://daesung.bstage.in/shop/products/62",
    "https://daesung.bstage.in/shop/products/63",
    "https://daesung.bstage.in/shop/products/64",
]

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
STATE_FILE = "state.json"


def send_telegram(message: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("尚未設定 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID，略過推播。")
        return

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        print("Telegram 推播狀態碼:", resp.status)


def fetch_out_of_stock(url: str) -> bool | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    match = re.search(r'"outOfStock"\s*:\s*(true|false)', html, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower() == "true"


def load_states() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "items" in data and isinstance(data["items"], dict):
        return data["items"]
    return {}


def save_states(items_state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"items": items_state}, f, ensure_ascii=False, indent=2)


def main() -> None:
    prev_items = load_states()
    curr_items = dict(prev_items)

    for url in URLS:
        prev_status = prev_items.get(url, "unknown")
        try:
            is_out = fetch_out_of_stock(url)
        except Exception as e:
            print(f"[{url}] 讀取失敗，保留前次狀態 ({prev_status})。原因: {e}")
            curr_items[url] = prev_status
            continue

        if is_out is None:
            print(f"[{url}] 找不到 outOfStock 欄位，保留前次狀態 ({prev_status})。")
            curr_items[url] = prev_status
            continue

        curr_status = "sold_out" if is_out else "available"
        print(f"[{url}] 上次: {prev_status} -> 本次: {curr_status}")
        curr_items[url] = curr_status

        if prev_status == "sold_out" and curr_status == "available":
            send_telegram(f"🚨 商品補貨／可購買了！快去看看：\n{url}")
        elif prev_status == "unknown" and curr_status == "available":
            send_telegram(f"ℹ️ 首次監測顯示可購買：\n{url}")

    save_states(curr_items)


if __name__ == "__main__":
    main()
