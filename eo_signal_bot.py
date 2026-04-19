import asyncio
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import yfinance as yf
from telegram import Bot
from telegram.error import TelegramError

TELEGRAM_TOKEN = "8672597127:AAGY1qP7vazLu55TZAKCcwEMWox0atmIg7o"
CHAT_ID = "1686839417"
ASSETS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/CHF": "EURCHF=X",
    "AUD/CAD": "AUDCAD=X",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "BRENT OIL": "BZ=F",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "TESLA": "TSLA",
    "GOOGLE": "GOOGL",
    "META": "META",
    "AMAZON": "AMZN",
    "NVIDIA": "NVDA",
    "DISNEY": "DIS",
    "SAUDI ARAMCO": "2222.SR",
}
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger(prices, period=20, std=2):
    sma = prices.rolling(period).mean()
    std_dev = prices.rolling(period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower

def analyze_asset(ticker_symbol, asset_name):
    try:
        df = yf.download(ticker_symbol, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 30:
            return None
        close = df["Close"].squeeze()
        high = df["High"].squeeze()
        low = df["Low"].squeeze()
        rsi = calculate_rsi(close).iloc[-1]
        macd_line, signal_line, histogram = calculate_macd(close)
        upper_bb, mid_bb, lower_bb = calculate_bollinger(close)
        current_price = close.iloc[-1]
        prev_price = close.iloc[-2]
        price_change = ((current_price - prev_price) / prev_price) * 100
        macd_val = macd_line.iloc[-1]
        sig_val = signal_line.iloc[-1]
        hist_val = histogram.iloc[-1]
        upper_val = upper_bb.iloc[-1]
        lower_val = lower_bb.iloc[-1]
        buy_score = 0
        sell_score = 0
        if rsi < 30:
            buy_score += 3
        elif rsi < 40:
            buy_score += 1
        elif rsi > 70:
            sell_score += 3
        elif rsi > 60:
            sell_score += 1
        if macd_val > sig_val and hist_val > 0:
            buy_score += 2
        elif macd_val < sig_val and hist_val < 0:
            sell_score += 2
        if current_price <= lower_val:
            buy_score += 3
        elif current_price >= upper_val:
            sell_score += 3
        if buy_score > sell_score and buy_score >= 5:
            direction = "BUY"
            confidence = min(int((buy_score / 10) * 100), 99)
        elif sell_score > buy_score and sell_score >= 5:
            direction = "SELL"
            confidence = min(int((sell_score / 10) * 100), 99)
        else:
            return None
        if confidence >= 85:
            presses = 10
            strength = "قوية جداً 🔥"
        elif confidence >= 70:
            presses = 7
            strength = "قوية 💪"
        elif confidence >= 55:
            presses = 5
            strength = "متوسطة ⚡"
        else:
            return None
        return {"asset": asset_name, "direction": direction, "price": current_price, "change": price_change, "rsi": rsi, "macd": macd_val, "confidence": confidence, "strength": strength, "presses": presses}
    except Exception as e:
        logging.warning(f"خطأ في {asset_name}: {e}")
        return None

def format_signal(signal):
    arrow = "🟢 شراء ↑" if signal["direction"] == "BUY" else "🔴 بيع ↓"
    time_now = datetime.now().strftime("%H:%M:%S")
    msg = f"{'='*30}\n{arrow}  —  {signal['asset']}\n{'='*30}\n💰 السعر: {signal['price']:.5f}\n📈 التغيير: {signal['change']:+.3f}%\n📊 RSI: {signal['rsi']:.1f}\n💪 القوة: {signal['strength']}\n✅ الثقة: {signal['confidence']}%\n🖱 الضغطات: {signal['presses']}\n⏱ المدة: دقيقة أو دقيقتين\n⏰ {time_now}\n{'='*30}\n⚠️ ادخل خلال 15 ثانية"
    return msg

async def run_bot():
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="🚀 EO Signal Bot شغّال!\nيراقب كل الأصول 24/7\nانتظر أول إشارة...")
    last_signals = {}
    while True:
        for asset_name, ticker in ASSETS.items():
            signal = analyze_asset(ticker, asset_name)
            if signal:
                key = f"{asset_name}_{signal['direction']}"
                now = datetime.now()
                if key in last_signals:
                    if (now - last_signals[key]).seconds < 300:
                        continue
                try:
                    await bot.send_message(chat_id=CHAT_ID, text=format_signal(signal))
                    last_signals[key] = now
                except TelegramError as e:
                    logging.error(f"خطأ: {e}")
            await asyncio.sleep(1)
        await asyncio.sleep(30)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    asyncio.run(run_bot())
