import pandas as pd
import numpy as np


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators."""
    df = df.copy()
    close = df["Close"]

    # ── Moving Averages ──────────────────────────────────────────────────────
    df["MA50"]  = close.rolling(window=50,  min_periods=1).mean()
    df["MA200"] = close.rolling(window=200, min_periods=1).mean()

    # ── RSI (14) ─────────────────────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # ── MACD ─────────────────────────────────────────────────────────────────
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]

    # ── Bollinger Bands (20, 2σ) ─────────────────────────────────────────────
    ma20         = close.rolling(window=20, min_periods=1).mean()
    std20        = close.rolling(window=20, min_periods=1).std()
    df["BB_mid"]   = ma20
    df["BB_upper"] = ma20 + 2 * std20
    df["BB_lower"] = ma20 - 2 * std20
    df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / ma20

    # ── Volume SMA ───────────────────────────────────────────────────────────
    df["Vol_MA20"] = df["Volume"].rolling(window=20, min_periods=1).mean()

    return df


def calculate_score(df: pd.DataFrame, fund: dict) -> dict:
    """
    Calculate a buy/sell/hold score from 0–100.
    Breakdown:
        RSI signal         0–20
        MACD signal        0–20
        Trend (MA)         0–20
        Fundamentals       0–25
        Bollinger          0–15
    """
    last = df.iloc[-1]
    score = 0
    breakdown = []

    # ── 1. RSI (max 20) ──────────────────────────────────────────────────────
    rsi = last.get("RSI", 50)
    if rsi < 30:        rsi_score = 20   # stark überverkauft → Kaufsignal
    elif rsi < 40:      rsi_score = 15
    elif rsi < 50:      rsi_score = 10
    elif rsi < 60:      rsi_score = 8
    elif rsi < 70:      rsi_score = 5
    else:               rsi_score = 0   # überkauft → Verkaufssignal
    score += rsi_score
    breakdown.append(("RSI Signal", rsi_score, 20))

    # ── 2. MACD (max 20) ─────────────────────────────────────────────────────
    macd   = last.get("MACD", 0)
    signal = last.get("MACD_signal", 0)
    hist   = last.get("MACD_hist", 0)
    # Crossover bullish?
    prev_hist = df["MACD_hist"].iloc[-2] if len(df) > 2 else hist
    macd_score = 0
    if macd > signal:
        macd_score += 10
    if hist > 0 and prev_hist <= 0:   # frischer bullisher Crossover
        macd_score += 10
    elif hist > 0:
        macd_score += 5
    score += macd_score
    breakdown.append(("MACD Signal", macd_score, 20))

    # ── 3. Trend / Moving Averages (max 20) ──────────────────────────────────
    close = last["Close"]
    ma50  = last.get("MA50",  close)
    ma200 = last.get("MA200", close)
    trend_score = 0
    if close > ma50:   trend_score += 8
    if close > ma200:  trend_score += 8
    if ma50 > ma200:   trend_score += 4   # Golden Cross
    score += trend_score
    breakdown.append(("Trend (MA)", trend_score, 20))

    # ── 4. Fundamentals (max 25) ─────────────────────────────────────────────
    fund_score = 0
    try:
        pe = float(str(fund.get("pe_ratio", "")).replace("x", "").replace("N/A", ""))
        if   pe < 15:  fund_score += 10
        elif pe < 25:  fund_score += 7
        elif pe < 35:  fund_score += 3
    except Exception:
        fund_score += 5   # neutral wenn kein KGV

    try:
        div = str(fund.get("dividend_yield", "0%")).replace("%", "")
        dv  = float(div) if div not in ("N/A", "") else 0
        if   dv > 3:  fund_score += 8
        elif dv > 1:  fund_score += 5
        elif dv > 0:  fund_score += 2
    except Exception:
        pass

    try:
        beta = float(str(fund.get("beta", "1")).replace("N/A", "1"))
        if 0.5 <= beta <= 1.5:   fund_score += 7
        elif beta < 0.5:         fund_score += 4
    except Exception:
        fund_score += 3
    score += fund_score
    breakdown.append(("Fundamentaldaten", fund_score, 25))

    # ── 5. Bollinger Bands (max 15) ──────────────────────────────────────────
    bb_upper = last.get("BB_upper", close * 1.1)
    bb_lower = last.get("BB_lower", close * 0.9)
    bb_mid   = last.get("BB_mid",   close)
    bb_score = 0
    if close <= bb_lower * 1.01:   bb_score = 15   # nahe Unterband
    elif close <= bb_mid:          bb_score = 10
    elif close >= bb_upper * 0.99: bb_score = 0    # nahe Oberband
    else:                          bb_score = 5
    score += bb_score
    breakdown.append(("Bollinger Bands", bb_score, 15))

    # ── Signal ───────────────────────────────────────────────────────────────
    if   score >= 62:  signal_str = "KAUFEN"
    elif score <= 38:  signal_str = "VERKAUFEN"
    else:              signal_str = "HALTEN"

    return {
        "total_score": score,
        "signal":      signal_str,
        "breakdown":   breakdown
    }


def get_fundamental_data(info: dict) -> dict:
    """Extract and format fundamental data from yfinance info dict."""

    def fmt_large(n):
        if n is None: return "N/A"
        if n >= 1e12: return f"{n/1e12:.2f}T"
        if n >= 1e9:  return f"{n/1e9:.2f}B"
        if n >= 1e6:  return f"{n/1e6:.2f}M"
        return str(n)

    return {
        "market_cap":      fmt_large(info.get("marketCap")),
        "pe_ratio":        f"{info['trailingPE']:.1f}x"  if info.get("trailingPE")        else "N/A",
        "eps":             f"{info['trailingEps']:.2f}"  if info.get("trailingEps")        else "N/A",
        "dividend_yield":  f"{info['dividendYield']*100:.2f}%" if info.get("dividendYield") else "0%",
        "week_52_high":    f"{info['fiftyTwoWeekHigh']:.2f}"   if info.get("fiftyTwoWeekHigh") else "N/A",
        "week_52_low":     f"{info['fiftyTwoWeekLow']:.2f}"    if info.get("fiftyTwoWeekLow")  else "N/A",
        "beta":            f"{info['beta']:.2f}"  if info.get("beta")   else "N/A",
        "sector":          info.get("sector", "N/A"),
    }
