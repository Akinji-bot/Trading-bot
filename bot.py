import time
import requests
import pandas as pd
from pybit.unified_trading import HTTP

  #==========CONFIG==========
import os

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


symbol = "XAUT/USDT" or "BTC/USDT"

session = HTTP
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET

running = True
last_update_id = 0

# ========== TELEGRAM ==========
def send_msg(text):
    url = f"https://api.telegram.org/bot{8676737582:AAGzbAPLFF782ian-RK-TdOKUOy0-eViCu8}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

# ========== GET COMMANDS ==========
def check_commands():
    global running, last_update_id

    url = f"https://api.telegram.org/bot{8676737582:AAGzbAPLFF782ian-RK-TdOKUOy0-eViCu8}/getUpdates"
    res = requests.get(url).json()

    if "result" not in res:
        return

    for update in res["result"]:
        update_id = update["update_id"]

        if update_id <= last_update_id:
            continue

        last_update_id = update_id

        if "message" not in update:
            continue

        msg = update["message"]["text"].lower()

        if msg == "start":
            running = True
            send_msg("✅ Bot STARTED")

        elif msg == "stop":
            running = False
            send_msg("⛔ Bot STOPPED")

        elif msg == "status":
            state = "RUNNING 🟢" if running else "STOPPED 🔴"
            send_msg(f"📊 Bot Status: {state}")

# ========== DATA ==========
def get_data():
    data = session.get_kline(
        category="linear",
        symbol=symbol,
        interval="5",
        limit=100
    )

    df = pd.DataFrame(data["result"]["list"])
    df = df.iloc[:, :5]
    df.columns = ["time","open","high","low","close"]
    df = df.astype(float)

    return df

# ========== INDICATORS ==========
def indicators(df):
    df["mid"] = df["close"].rolling(20).mean()
    df["std"] = df["close"].rolling(20).std()
    df["upper"] = df["mid"] + 2 * df["std"]
    df["lower"] = df["mid"] - 2 * df["std"]

    low14 = df["low"].rolling(14).min()
    high14 = df["high"].rolling(14).max()
    df["stoch"] = 100 * (df["close"] - low14) / (high14 - low14)

    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    return df

# ========== TREND ==========
def trend(df):
    last = df.iloc[-1]

    if last["ema50"] > last["ema200"]:
        return "up"
    elif last["ema50"] < last["ema200"]:
        return "down"
    return "flat"

# ========== SIGNAL ==========
def signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    mid_lower = (last["lower"] + last["mid"]) / 2
    mid_upper = (last["upper"] + last["mid"]) / 2

    buy = (
        last["close"] > mid_lower and
        prev["stoch"] < 10 and
        last["stoch"] > prev["stoch"]
    )

    sell = (
        last["close"] < mid_upper and
        prev["stoch"] > 90 and
        last["stoch"] < prev["stoch"]
    )

    if buy:
        return "buy"
    if sell:
        return "sell"
    return "hold"

# ========== ORDER ==========
def place_order(side, price):
    qty = 0.01

    sl = price * (0.98 if side == "Buy" else 1.02)
    tp = price * (1.06 if side == "Buy" else 0.94)

    session.place_order(
        category="linear",
        symbol=symbol,
        side=side,
        orderType="Market",
        qty=qty,
        takeProfit=tp,
        stopLoss=sl
    )

    send_msg(f"📊 {symbol} {side} executed\nTP: {tp}\nSL: {sl}")

# ========== MAIN LOOP ==========
send_msg("🚀 Bot online. Send START / STOP / STATUS")

while True:
    try:
        check_commands()

        if not running:
            time.sleep(5)
            continue

        df = get_data()
        df = indicators(df)

        sig = signal(df)
        tr = trend(df)
        price = df.iloc[-1]["close"]

        print("Signal:", sig, "| Trend:", tr)

        if sig == "buy" and tr == "up":
            place_order("Buy", price)

        elif sig == "sell" and tr == "down":
            place_order("Sell", price)

        time.sleep(300)

    except Exception as e: 
send_msg(f"Error: {e}")
        time.sleep(60)
