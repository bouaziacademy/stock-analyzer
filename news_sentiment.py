"""
News & Sentiment Analyse für Stock Analyzer Pro
Verwendet Yahoo Finance News (kostenlos, kein API Key nötig)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import re


def get_sentiment_score(title: str) -> tuple:
    """
    Einfache Keyword-basierte Sentiment-Analyse.
    Gibt (score, label) zurück: score -1 bis +1
    """
    title_lower = title.lower()

    positive_words = [
        "surge", "soar", "jump", "rise", "gain", "profit", "beat", "growth",
        "record", "high", "bullish", "buy", "upgrade", "strong", "rally",
        "hausse", "montée", "bénéfice", "croissance", "record", "acheter",
        "sube", "gana", "beneficio", "crecimiento", "comprar", "alza",
        "steigt", "gewinn", "wachstum", "kaufen", "stark", "rekord"
    ]

    negative_words = [
        "fall", "drop", "decline", "loss", "miss", "weak", "sell", "downgrade",
        "crash", "risk", "bearish", "cut", "low", "concern", "warn", "fear",
        "baisse", "chute", "perte", "vendre", "faible", "risque", "crainte",
        "cae", "baja", "pérdida", "vender", "débil", "riesgo", "caída",
        "fällt", "verlust", "schwach", "verkaufen", "risiko", "warnung"
    ]

    pos_count = sum(1 for w in positive_words if w in title_lower)
    neg_count = sum(1 for w in negative_words if w in title_lower)

    if pos_count > neg_count:
        return 1, "positive"
    elif neg_count > pos_count:
        return -1, "negative"
    else:
        return 0, "neutral"


def get_news(ticker: str, max_news: int = 8) -> dict:
    """
    Holt News von Yahoo Finance und analysiert Sentiment.
    Gibt dict mit news liste und overall sentiment zurück.
    """
    try:
        stock = yf.Ticker(ticker)
        news_raw = stock.news

        if not news_raw:
            return {"news": [], "overall": "neutral", "score": 0}

        news_list = []
        total_score = 0

        for item in news_raw[:max_news]:
            title = item.get("title", "")
            if not title:
                continue

            score, label = get_sentiment_score(title)
            total_score += score

            # Datum formatieren
            pub_time = item.get("providerPublishTime", 0)
            try:
                date_str = datetime.fromtimestamp(pub_time).strftime("%d.%m.%Y %H:%M")
            except Exception:
                date_str = "N/A"

            news_list.append({
                "title":     title,
                "url":       item.get("link", "#"),
                "source":    item.get("publisher", "Unknown"),
                "date":      date_str,
                "sentiment": label,
                "score":     score
            })

        # Gesamt-Sentiment berechnen
        if total_score > 1:
            overall = "positive"
        elif total_score < -1:
            overall = "negative"
        else:
            overall = "neutral"

        return {
            "news":    news_list,
            "overall": overall,
            "score":   total_score
        }

    except Exception as e:
        return {"news": [], "overall": "neutral", "score": 0, "error": str(e)}
