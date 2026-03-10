# 📈 Stock Analyzer Pro

Ein vollständiges Aktienanalyse-Dashboard mit technischer und fundamentaler Analyse.

## 🚀 Installation & Start

### 1. Python-Pakete installieren
```bash
pip install -r requirements.txt
```

### 2. App starten
```bash
streamlit run app.py
```

Der Browser öffnet sich automatisch unter: **http://localhost:8501**

---

## 🎯 Funktionen

### Datenquellen
- **Yahoo Finance** (yfinance) – kostenlos, kein API-Key nötig
- Echtzeit- und historische Kursdaten
- Fundamentaldaten automatisch geladen

### Technische Indikatoren
| Indikator | Beschreibung |
|-----------|-------------|
| **MA 50 / MA 200** | Moving Averages – Trendrichtung |
| **RSI (14)** | Relative Strength Index – Überkauft/Überverkauft |
| **MACD** | Momentum-Indikator mit Signal & Histogramm |
| **Bollinger Bands** | Volatilitätsbänder (20 Tage, 2σ) |

### Scoring-System (0–100 Punkte)
| Kategorie | Max. Punkte |
|-----------|------------|
| RSI Signal | 20 |
| MACD Signal | 20 |
| Trend (MA50/MA200) | 20 |
| Fundamentaldaten | 25 |
| Bollinger Bands | 15 |

**Empfehlung:**
- ≥ 62 Punkte → 🟢 **KAUFEN**
- 39–61 Punkte → 🟡 **HALTEN**
- ≤ 38 Punkte → 🔴 **VERKAUFEN**

---

## 📁 Projektstruktur
```
stock_analyzer/
├── app.py           # Streamlit Dashboard
├── analysis.py      # Indikatoren & Scoring Engine
├── config.py        # Konfiguration & Schnellauswahl
├── requirements.txt # Python-Abhängigkeiten
└── README.md        # Diese Datei
```

---

## 🔮 Geplante Erweiterungen
- [ ] KI-Vorhersagen (LSTM / Prophet)
- [ ] Portfolio-Analyse
- [ ] News-Sentiment (NLP)
- [ ] Automatische E-Mail-Alerts
- [ ] Alpha Vantage / Finnhub API-Integration
- [ ] Risikoanalyse & Sharpe Ratio

---

## ⚠️ Disclaimer
Dieses Tool dient nur zu Informationszwecken und stellt keine Anlageberatung dar.
Investieren birgt Risiken. Bitte konsultieren Sie einen Finanzberater.
