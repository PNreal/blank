from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from binance.client import Client
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import os, time

# ==== Config ====
BOT_TOKEN = "8451682829:AAHl9hYQXpL6QOrb502XTQ9T2Ei0PyxeAOM"
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"

client = Client(API_KEY, API_SECRET)
USD_TO_VND = 25000

# ==== Hàm chung ====
def calculate_rsi(prices, period=21):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

symbols = [f"{s.lower()}usdt" for s in [
    "BTC", "YFI", "ETH", "BTCDOM",  "BNB", "BCH", "TAO", "AAVE", "SOL", "LTC", "HYPE",
     "COMP", "TRB", "BSV", "AVAX", "LINK", "ENS", "ETC", "METIS", "KSM", "GMX", "NMR", "EGLD",
     "INJ", "AUCTION", "UNI", "SSV", "ORDI", "TRUMP", "ZEN", "LPT",  "AR", "XVS", "MOVR",
     "ICP", "PENDLE", "ATOM", "APT", "VANA", "CVX", "DOT", "RAY", "GAS", "SUI",  "TON",
     "QTUM", "XRP", "FXS",  "CAKE", "AXS", "NEAR", "FIL",  "MORHO", "JTO", "ZRO",
     "CYBER", "ETHW", "TIA", "UMA", "MASK", "EIGEN", "RUNE", "LDO",  "KAITO", "VIRTUAL",
     "ETHFI", "ONDO", "WLD", "ADA", "BAND", "WIF", "LQTY",  "NXPC", "FARTCOIN", "SUSHI",
     "BNT", "TWT", "MTL", "OP", "AGLD", "SNX", "ME", "ENA", "STX", "DYDX", "SUPER", "IO",
     "IMX", "RONIN", "ARB", "RED", "SYRUP", "JUP", "ARKM", "ARK",
     "KNC",  "KAVA", "ALICE", "INIT", "XLM",  "TRX", "COW", "SCR", "HYPER",
     "UXLINK",  "NIL", "NEWT", "SEI", "POL", "SAND", "LISTA",
     "ZRX",  "STORJ", "POPCAT", "1INCH", "SAGA",  "GLM", "HBAR", "DOGE", 
     "OM",   "PNUT", "MANTA", "MAGIC", "SONIC", "CFX", "IOTA", "JOE", "ZETA","SOMI",
     "MINA", "PYTH", "SXP", "ONG", "ID", "STG",   "POWR", "YGG", "LUNA",
     "TA", "MOODENG", "BB", "POLYX", "ICX", "AI", "STRK",  "MOVE",
     "MERL",   "AIXBT", "NTRN", "CATI",  "1000FLOKI",
     "STO",  "AEVO", "GRT", "CETUS", "FIDA", "KAS",  "GOAT",  "SLERF", "HFT",
     "SXT", "BLUR",  "SIGN", "MAV", "WOO", "MOCA", 
     "USUAL", "ZK", "1000LUNC",   "RIF", "RARE", "BIGTIME", "COTI", "C98", "XAI",
     "BRETT",  "ATA",   "GMT", "CHZ", "ACT", "ALT", 
     "SOPH",  "PIXEL", "TRU", "HUMA", "NKN", "AVAAI", "ROSE", "1000BONK",
     "WAXP", "ACH",  "PEOPLE", "ARC", "T", "GALA",
     "JASMY", "USTC",  "1000SHIB", "G", "ZIL", "ONE", "1000PEPE", "CELR", "CKB",
     "PUMP", "IOST", "MEME"
]]

# ==== Các hàm scan gốc ====
def scan_rsi_15m_under30():
    return scan(symbols, Client.KLINE_INTERVAL_15MINUTE, 30, "lt")

def scan_rsi_15m_over70():
    return scan(symbols, Client.KLINE_INTERVAL_15MINUTE, 70, "gt")

def scan_rsi_h4_under30():
    return scan(symbols, Client.KLINE_INTERVAL_4HOUR, 30, "lt")

def scan_rsi_h4_over70():
    return scan(symbols, Client.KLINE_INTERVAL_4HOUR, 70, "gt")

def scan(symbols, interval, threshold, mode):
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, interval, threshold, mode): s for s in symbols}
        for f in as_completed(futures):
            r = f.result()
            if r: results.append(r)
    return sorted(results, key=lambda x: x['rsi'], reverse=(mode=="gt"))

def process_symbol(symbol, interval, threshold, mode):
    try:
        klines = client.futures_klines(symbol=symbol, interval=interval, limit=50)
        closes = pd.Series([float(k[4]) for k in klines])
        rsi = calculate_rsi(closes).iloc[-1]
        if (mode=="lt" and rsi < threshold) or (mode=="gt" and rsi > threshold):
            return {"symbol": symbol, "rsi": rsi}
    except Exception as e:
        print(f"Lỗi {symbol}: {e}")
    return None

# ==== Các hàm bổ sung (RSI 15m+4h đồng thời) ====
def scan_rsi_both_under30():
    results = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(process_symbol_both, symbol, "lt"): symbol for symbol in symbols}
        for f in as_completed(futures):
            r = f.result()
            if r: results.append(r)
    return sorted(results, key=lambda x: x['rsi_4h'])

def scan_rsi_both_over70():
    results = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(process_symbol_both, symbol, "gt"): symbol for symbol in symbols}
        for f in as_completed(futures):
            r = f.result()
            if r: results.append(r)
    return sorted(results, key=lambda x: x['rsi_4h'], reverse=True)

def process_symbol_both(symbol, mode):
    try:
        klines_15m = client.futures_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
        closes_15m = pd.Series([float(k[4]) for k in klines_15m])
        rsi_15m = calculate_rsi(closes_15m).iloc[-1]

        klines_4h = client.futures_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_4HOUR, limit=50)
        closes_4h = pd.Series([float(k[4]) for k in klines_4h])
        rsi_4h = calculate_rsi(closes_4h).iloc[-1]

        if (mode=="lt" and rsi_15m < 30 and rsi_4h < 30) or \
           (mode=="gt" and rsi_15m > 70 and rsi_4h > 70):
            return {"symbol": symbol.upper(), "rsi_15m": round(rsi_15m, 2), "rsi_4h": round(rsi_4h, 2)}
    except Exception as e:
        print(f"Lỗi xử lý {symbol}: {e}")
    return None

# ==== Telegram Bot ====
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lấy dữ liệu BTC
    try:
        klines_15m = client.futures_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
        closes_15m = pd.Series([float(k[4]) for k in klines_15m])
        rsi_15m = calculate_rsi(closes_15m).iloc[-1]

        klines_4h = client.futures_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_4HOUR, limit=50)
        closes_4h = pd.Series([float(k[4]) for k in klines_4h])
        rsi_4h = calculate_rsi(closes_4h).iloc[-1]

        btc_text = f"BTC RSI: 15m={rsi_15m:.2f}, 4h={rsi_4h:.2f}"
    except Exception as e:
        btc_text = f"RSI BTC: {e}"

    # Keyboard menu
    keyboard = [
        [InlineKeyboardButton("15m RSI<30", callback_data="rsi_15m_lt30"),
         InlineKeyboardButton("15m RSI>70", callback_data="rsi_15m_gt70")],
        [InlineKeyboardButton("H4 RSI<30", callback_data="rsi_h4_lt30"),
         InlineKeyboardButton("H4 RSI>70", callback_data="rsi_h4_gt70")],
        [InlineKeyboardButton("15m&4h<30", callback_data="rsi_both_lt30"),
         InlineKeyboardButton("15m&4h>70", callback_data="rsi_both_gt70")]
    ]
    await update.message.reply_text(btc_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "rsi_15m_lt30": results = scan_rsi_15m_under30()
    elif choice == "rsi_15m_gt70": results = scan_rsi_15m_over70()
    elif choice == "rsi_h4_lt30": results = scan_rsi_h4_under30()
    elif choice == "rsi_h4_gt70": results = scan_rsi_h4_over70()
    elif choice == "rsi_both_lt30": results = scan_rsi_both_under30()
    elif choice == "rsi_both_gt70": results = scan_rsi_both_over70()
    else: results = []

    text = "\n".join([
        f"{r.get('symbol', '?')}: 15m={r.get('rsi_15m', r.get('rsi','?')):.1f}, 4h={r.get('rsi_4h', r.get('rsi','?')):.1f}"
        for r in results[:10]
    ]) or "No results found."
    await query.edit_message_text(f"{choice}:\n{text}")

# ==== Run bot ====
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", menu))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CallbackQueryHandler(button_callback))
app.run_polling()
