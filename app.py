import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf
from analysis import calculate_indicators, calculate_score, get_fundamental_data
from config import POPULAR_STOCKS
from translations import TRANSLATIONS, LANGUAGE_NAMES, t
from news_sentiment import get_news

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📈 Stock Analyzer Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid #2d3250;
        margin-bottom: 10px;
    }
    .metric-label { color: #8b8fa8; font-size: 12px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
    .metric-value { color: #ffffff; font-size: 24px; font-weight: 700; margin-top: 4px; }
    .metric-delta-pos { color: #00d4aa; font-size: 13px; }
    .metric-delta-neg { color: #ff4b6e; font-size: 13px; }
    .signal-buy  { background: linear-gradient(135deg, #00d4aa22, #00d4aa44); border: 1px solid #00d4aa; border-radius: 10px; padding: 12px 20px; color: #00d4aa; font-size: 20px; font-weight: 700; text-align: center; }
    .signal-sell { background: linear-gradient(135deg, #ff4b6e22, #ff4b6e44); border: 1px solid #ff4b6e; border-radius: 10px; padding: 12px 20px; color: #ff4b6e; font-size: 20px; font-weight: 700; text-align: center; }
    .signal-hold { background: linear-gradient(135deg, #f5a62322, #f5a62344); border: 1px solid #f5a623; border-radius: 10px; padding: 12px 20px; color: #f5a623; font-size: 20px; font-weight: 700; text-align: center; }
    .score-bar-bg { background: #1e2130; border-radius: 8px; height: 14px; width: 100%; margin-top: 6px; }
    .section-title { color: #a0a4c0; font-size: 13px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin: 20px 0 10px 0; border-bottom: 1px solid #2d3250; padding-bottom: 6px; }
    div[data-testid="stMetricValue"] { font-size: 22px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session State initialisieren ───────────────────────────────────────────
if "ticker_value" not in st.session_state:
    st.session_state.ticker_value = "AAPL"
if "lang" not in st.session_state:
    st.session_state.lang = "en"

def set_ticker(sym):
    st.session_state.ticker_value = sym

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Stock Analyzer Pro")
    lang = st.selectbox(
        "🌍 Language / Sprache / Langue / Idioma",
        options=list(LANGUAGE_NAMES.keys()),
        format_func=lambda x: LANGUAGE_NAMES[x],
        index=list(LANGUAGE_NAMES.keys()).index(st.session_state.lang)
    )
    st.session_state.lang = lang
    st.markdown("---")

    ticker_input = st.text_input(
        t("ticker_label", lang),
        value=st.session_state.ticker_value,
        placeholder=t("ticker_placeholder", lang)
    ).upper().strip()

    if ticker_input:
        st.session_state.ticker_value = ticker_input

    st.markdown(t("quick_select", lang))
    cols = st.columns(3)
    for i, (name, sym) in enumerate(POPULAR_STOCKS.items()):
        if cols[i % 3].button(sym, width='stretch', key=f"btn_{sym}"):
            set_ticker(sym)
            st.rerun()

    st.markdown("---")
    period = st.selectbox(
        t("period_label", lang),
        ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=3,
        format_func=lambda x: {
            "1mo": t("periods", lang)["1mo"], "3mo": "3 Monate", "6mo": "6 Monate",
            "1y": "1 Jahr", "2y": "2 Jahre", "5y": "5 Jahre"
        }[x]
    )
    if period in ["1mo", "3mo"]:
        st.warning(t("warning_period", lang))

    show_ma      = st.checkbox(t("show_ma", lang), value=True)
    show_bb      = st.checkbox(t("show_bb", lang), value=True)
    show_volume  = st.checkbox(t("show_volume", lang), value=True)
    show_rsi     = st.checkbox("RSI", value=True)
    show_macd    = st.checkbox("MACD", value=True)

    analyze_btn = st.button(t("analyze_btn", lang), width='stretch', type="primary")

# ─── Main ────────────────────────────────────────────────────────────────────
st.title(t("app_title", lang))

if analyze_btn:
    st.session_state.ticker = st.session_state.ticker_value

if "ticker" not in st.session_state:
    st.session_state.ticker = st.session_state.ticker_value

ticker = st.session_state.get("ticker", "AAPL")

@st.cache_data(ttl=300)
def load_data(sym, period):
    try:
        stock = yf.Ticker(sym)
        hist  = stock.history(period=period)
        info  = stock.info
        return hist, info
    except Exception as e:
        return None, {}

with st.spinner(f"⏳ Lade Daten für **{ticker}**..."):
    hist, info = load_data(ticker, period)

if hist is None or hist.empty:
    st.error(f"❌ Keine Daten für **{ticker}** gefunden. Bitte Ticker prüfen.")
    st.stop()

# ─── Indicators & Score ──────────────────────────────────────────────────────
df   = calculate_indicators(hist)
fund = get_fundamental_data(info)
score_data = calculate_score(df, fund)

# ─── Header Row ──────────────────────────────────────────────────────────────
company_name = info.get("longName", ticker)
current_price = df["Close"].iloc[-1]
prev_price    = df["Close"].iloc[-2]
price_change  = current_price - prev_price
pct_change    = (price_change / prev_price) * 100
currency      = info.get("currency", "USD")

st.markdown(f"### {company_name} &nbsp; `{ticker}`")

c1, c2, c3, c4, c5 = st.columns(5)
delta_color = "metric-delta-pos" if price_change >= 0 else "metric-delta-neg"
delta_sign  = "▲" if price_change >= 0 else "▼"

def mcard(col, label, value, delta=None, delta_class=""):
    # Native Streamlit metric - kein HTML nötig
    col.metric(label=label, value=value, delta=delta)

mcard(c1, "Kurs", f"{current_price:.2f} {currency}",
      f"{delta_sign} {abs(price_change):.2f} ({pct_change:+.2f}%)", delta_color)
mcard(c2, "Marktkapitalisierung", f"{fund.get('market_cap', 'N/A')}")
mcard(c3, "KGV (P/E)", f"{fund.get('pe_ratio', 'N/A')}")
mcard(c4, "EPS", f"{fund.get('eps', 'N/A')}")
mcard(c5, "Dividende", f"{fund.get('dividend_yield', 'N/A')}")

# ─── Signal + Score ──────────────────────────────────────────────────────────
st.markdown("---")
col_sig, col_score, col_detail = st.columns([1, 1, 2])

signal = score_data["signal"]
score  = score_data["total_score"]
sig_class = {"KAUFEN": "signal-buy", "VERKAUFEN": "signal-sell", "HALTEN": "signal-hold"}[signal]
sig_emoji = {"KAUFEN": "🟢", "VERKAUFEN": "🔴", "HALTEN": "🟡"}[signal]

with col_sig:
    st.markdown(f"#### {t('recommendation', lang)}")
    signal_map = {"KAUFEN": "signal_buy", "VERKAUFEN": "signal_sell", "HALTEN": "signal_hold",
                   "BUY": "signal_buy", "SELL": "signal_sell", "HOLD": "signal_hold"}
    signal_text = t(signal_map.get(signal, "signal_hold"), lang)
    st.markdown(f"## {signal_text}")

with col_score:
    st.markdown(f"#### {t('total_score', lang)}")
    st.markdown(f"## {score} / 100")
    st.progress(score / 100)

with col_detail:
    st.markdown(f"#### {t('score_breakdown', lang)}")
    for name, val, max_val in score_data["breakdown"]:
        pct = val / max_val
        st.caption(f"{name}: {val}/{max_val}")
        st.progress(pct)

# ─── Main Chart ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"#### {t('chart_title', lang)}")

rows, row_heights = 1, [0.6]
if show_volume: rows += 1; row_heights.append(0.15)
if show_rsi:    rows += 1; row_heights.append(0.12)
if show_macd:   rows += 1; row_heights.append(0.13)

subplot_titles = ["Kurs"]
if show_volume: subplot_titles.append(t("show_volume", lang))
if show_rsi:    subplot_titles.append("RSI")
if show_macd:   subplot_titles.append("MACD")

fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                    row_heights=row_heights, vertical_spacing=0.03,
                    subplot_titles=subplot_titles)

# Candlestick
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    increasing_line_color="#00d4aa", decreasing_line_color="#ff4b6e",
    name="Kurs"
), row=1, col=1)

if show_ma and "MA50" in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"],  line=dict(color="#f5a623", width=1.5), name="MA 50"),  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA200"], line=dict(color="#c084fc", width=1.5), name="MA 200"), row=1, col=1)

if show_bb and "BB_upper" in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], line=dict(color="#60a5fa", width=1, dash="dot"), name="BB Oben"),  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"], line=dict(color="#60a5fa", width=1, dash="dot"), name="BB Unten", fill="tonexty", fillcolor="rgba(96,165,250,0.05)"), row=1, col=1)

row_idx = 2
if show_volume:
    colors = ["#00d4aa" if c >= o else "#ff4b6e" for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=colors, name=t("show_volume", lang), opacity=0.7), row=row_idx, col=1)
    row_idx += 1

if show_rsi and "RSI" in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], line=dict(color="#a78bfa", width=1.5), name="RSI"), row=row_idx, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff4b6e", line_width=1, row=row_idx, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00d4aa", line_width=1, row=row_idx, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="#ff4b6e", opacity=0.05, row=row_idx, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="#00d4aa", opacity=0.05, row=row_idx, col=1)
    row_idx += 1

if show_macd and "MACD" in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"],        line=dict(color="#00d4aa", width=1.5), name="MACD"),   row=row_idx, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], line=dict(color="#f5a623", width=1.5), name="Signal"), row=row_idx, col=1)
    macd_hist_colors = ["#00d4aa" if v >= 0 else "#ff4b6e" for v in df["MACD_hist"]]
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], marker_color=macd_hist_colors, name="MACD Hist", opacity=0.6), row=row_idx, col=1)

fig.update_layout(
    height=700,
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font=dict(color="#a0a4c0", size=11),
    legend=dict(bgcolor="#1e2130", bordercolor="#2d3250", borderwidth=1, orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=10),
)
fig.update_xaxes(gridcolor="#1e2130", showgrid=True)
fig.update_yaxes(gridcolor="#1e2130", showgrid=True)

st.plotly_chart(fig, width='stretch')

# ─── Fundamental + Technical Details ─────────────────────────────────────────
st.markdown("---")
col_fund, col_tech = st.columns(2)

with col_fund:
    st.markdown(f"#### {t('fund_title', lang)}")
    fund_df = pd.DataFrame({
        "Kennzahl": ["Marktkapitalisierung", "KGV", "EPS", "Dividendenrendite",
                     "52W Hoch", "52W Tief", "Beta", "Sektor"],
        "Wert": [
            fund.get("market_cap", "N/A"), fund.get("pe_ratio", "N/A"),
            fund.get("eps", "N/A"), fund.get("dividend_yield", "N/A"),
            fund.get("week_52_high", "N/A"), fund.get("week_52_low", "N/A"),
            fund.get("beta", "N/A"), fund.get("sector", "N/A")
        ]
    })
    st.dataframe(fund_df, hide_index=True, width='stretch')

with col_tech:
    st.markdown(f"#### {t('tech_title', lang)}")
    last = df.iloc[-1]
    rsi_val  = last.get("RSI", np.nan)
    macd_val = last.get("MACD", 0)
    sig_val  = last.get("MACD_signal", 0)
    ma50     = last.get("MA50", np.nan)
    ma200    = last.get("MA200", np.nan)
    close    = last["Close"]

    def sig_label(condition_buy, condition_sell):
        if condition_buy:  return "🟢 Bullish"
        if condition_sell: return "🔴 Bearish"
        return "🟡 Neutral"

    tech_df = pd.DataFrame({
        "Indikator": ["RSI (14)", "MACD", "MA50 vs Kurs", "MA50 vs MA200", "Bollinger"],
        "Wert": [
            f"{rsi_val:.1f}" if not np.isnan(rsi_val) else "N/A",
            f"{macd_val:.3f}",
            f"{ma50:.2f}" if not np.isnan(ma50) else "N/A",
            f"MA50: {ma50:.2f} | MA200: {ma200:.2f}" if not (np.isnan(ma50) or np.isnan(ma200)) else "N/A",
            f"{'Nahe Unterband' if close <= last.get('BB_lower', 0)*1.01 else 'Nahe Oberband' if close >= last.get('BB_upper', 0)*0.99 else 'Mitte'}"
        ],
        "Signal": [
            sig_label(rsi_val < 30, rsi_val > 70),
            sig_label(macd_val > sig_val, macd_val < sig_val),
            sig_label(close > ma50, close < ma50),
            sig_label(ma50 > ma200, ma50 < ma200) if not (np.isnan(ma50) or np.isnan(ma200)) else "🟡 N/A",
            sig_label(close <= last.get("BB_lower", 0)*1.01, close >= last.get("BB_upper", 0)*0.99)
        ]
    })
    st.dataframe(tech_df, hide_index=True, width='stretch')

# ─── KI Vorhersage (LSTM) ────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"#### {t('ai_title', lang)}")

col_lstm_info, col_lstm_btn = st.columns([3, 1])
with col_lstm_info:
    st.markdown("""
    <div style="background:#1e2130;border-radius:10px;padding:12px 16px;border:1px solid #2d3250;font-size:13px;color:#a0a4c0;">
    {t("ai_description", lang)}
    </div>
    """, unsafe_allow_html=True)

with col_lstm_btn:
    run_lstm = st.button(t("ai_start", lang), width='stretch', type="primary")

forecast_days = int(st.slider(t("forecast_label", lang), min_value=7, max_value=60, value=30, step=7))
lstm_epochs = int(st.select_slider(t("epochs_label", lang),
                                  options=["10", "20", "30", "50", "75", "100"], value="30"))

if run_lstm:
    with st.spinner(t("ai_loading", lang)):
        try:
            from lstm_predictor import predict_lstm
            result = predict_lstm(df, forecast_days=int(forecast_days), epochs=int(lstm_epochs))

            if "error" in result:
                st.error(f"❌ {result['error']}")
            else:
                # ── Metriken ─────────────────────────────────────────────────
                m1, m2, m3, m4 = st.columns(4)
                last_real  = result["close_hist"][-1]
                last_pred  = result["close_pred"][-1]
                pred_delta = ((last_pred - last_real) / last_real) * 100
                pred_sign  = "▲" if pred_delta >= 0 else "▼"
                pred_color = "#00d4aa" if pred_delta >= 0 else "#ff4b6e"

                mcard(m1, t("current_price_card", lang),   f"{last_real:.2f} {currency}")
                mcard(m2, f"Prognose +{forecast_days}T",
                      f"{last_pred:.2f} {currency}",
                      f"{pred_sign} {abs(pred_delta):.1f}%",
                      "metric-delta-pos" if pred_delta >= 0 else "metric-delta-neg")
                mcard(m3, t("accuracy_card", lang), f"{result['accuracy']:.1f}%")
                mcard(m4, t("error_range", lang), f"{result['std_err']:.2f} {currency}")

                # ── Vorhersage-Chart ──────────────────────────────────────────
                fig_lstm = go.Figure()

                # Historische Kurse
                fig_lstm.add_trace(go.Scatter(
                    x=result["dates_hist"], y=result["close_hist"],
                    line=dict(color="#60a5fa", width=2),
                    name=t("real_price", lang)
                ))

                # Konfidenzband
                _dates_fwd  = [str(d) for d in result["dates_pred"]]
                _dates_back = _dates_fwd[::-1]
                _upper      = [float(v) for v in result["conf_upper"]]
                _lower      = [float(v) for v in result["conf_lower"]]
                fig_lstm.add_trace(go.Scatter(
                    x=_dates_fwd + _dates_back,
                    y=_upper + _lower[::-1],
                    fill="toself",
                    fillcolor="rgba(192,132,252,0.15)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name=t("confidence", lang)
                ))

                # Vorhersage-Linie
                fig_lstm.add_trace(go.Scatter(
                    x=result["dates_pred"], y=result["close_pred"],
                    line=dict(color="#c084fc", width=2.5, dash="dash"),
                    name=f"KI-Prognose ({forecast_days} Tage)"
                ))

                # Trennlinie heute als vertikale Linie (Scatter)
                today_x = str(result["dates_hist"][-1])
                fig_lstm.add_trace(go.Scatter(
                    x=[today_x, today_x],
                    y=[min(result["close_hist"]) * 0.97, max(result["close_hist"]) * 1.03],
                    mode="lines",
                    line=dict(color="#f5a623", width=1.5, dash="dot"),
                    name=t("today", lang)
                ))

                fig_lstm.update_layout(
                    height=420,
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    font=dict(color="#a0a4c0", size=11),
                    legend=dict(bgcolor="#1e2130", bordercolor="#2d3250", borderwidth=1),
                    margin=dict(l=10, r=10, t=20, b=10),
                    xaxis=dict(gridcolor="#1e2130"),
                    yaxis=dict(gridcolor="#1e2130", title=f"Kurs ({currency})")
                )
                st.plotly_chart(fig_lstm, width='stretch')

                # ── Training Loss Chart ───────────────────────────────────────
                with st.expander(t("training_history", lang)):
                    fig_loss = go.Figure()
                    fig_loss.add_trace(go.Scatter(
                        y=result["train_loss"], line=dict(color="#00d4aa", width=2), name="Training Loss"
                    ))
                    if result["val_loss"]:
                        fig_loss.add_trace(go.Scatter(
                            y=result["val_loss"], line=dict(color="#f5a623", width=2), name="Validation Loss"
                        ))
                    fig_loss.update_layout(
                        height=250, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                        font=dict(color="#a0a4c0"), margin=dict(l=10, r=10, t=10, b=10),
                        xaxis=dict(gridcolor="#1e2130", title="Epoche"),
                        yaxis=dict(gridcolor="#1e2130", title="Loss (MSE)")
                    )
                    st.plotly_chart(fig_loss, width='stretch')
                    st.markdown(f"""
                    <div style="color:#8b8fa8;font-size:12px;">
                    📊 <b>MAPE:</b> {result['mape']}% &nbsp;|&nbsp;
                    🎯 <b>Genauigkeit:</b> {result['accuracy']}% &nbsp;|&nbsp;
                    📐 <b>Epochen:</b> {lstm_epochs}
                    </div>
                    """, unsafe_allow_html=True)

                st.info(t("ai_hint", lang))

        except ImportError:
            st.warning("⚠️ TensorFlow nicht verfügbar in der Cloud-Version. Bitte lokal ausführen für KI-Vorhersage.")
        except Exception as e:
            import traceback
            st.error(f"❌ Fehler beim Training: {str(e)}")
            st.code(traceback.format_exc())

# ─── News & Sentiment ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"#### {t('news_title', lang)}")

with st.spinner(t("news_loading", lang)):
    news_data = get_news(ticker)

if news_data.get("error"):
    st.warning(f"⚠️ {t('news_none', lang)} ({news_data['error'][:100]})")
elif not news_data["news"]:
    st.info(t("news_none", lang))
    st.caption(f"Ticker: {ticker} — Yahoo Finance hat keine News zurückgegeben.")
else:
    # Gesamt Sentiment
    overall = news_data["overall"]
    score   = news_data["score"]
    sentiment_map = {
        "positive": t("news_positive", lang),
        "negative": t("news_negative", lang),
        "neutral":  t("news_neutral",  lang)
    }
    st.metric(t("news_overall", lang), sentiment_map.get(overall, "🟡"))

    # News Karten
    for i, news in enumerate(news_data["news"]):
        sent  = news["sentiment"]
        color = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}.get(sent, "🟡")
        with st.expander(f"{color} {news['title']}"):
            st.caption(f"📅 {news['date']} | 📰 {news['source']}")
            st.markdown(f"[{t('news_read_more', lang)}]({news['url']})")

# ─── Portfolio Tracker ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"#### {t('portfolio_title', lang)}")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# Aktie hinzufügen - direkt sichtbar ohne Expander
st.markdown(f"**{t('portfolio_add', lang)}**")
col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
p_ticker = col_p1.text_input(t("portfolio_ticker", lang), placeholder="AAPL", key="p_ticker").upper().strip()
p_shares = col_p2.number_input(t("portfolio_shares", lang), min_value=0.01, value=10.0, step=1.0, key="p_shares")
p_price  = col_p3.number_input(t("portfolio_price", lang),  min_value=0.01, value=100.0, step=1.0, key="p_price")
if col_p4.button(t("portfolio_add_btn", lang), type="primary", key="btn_add_stock"):
    if p_ticker:
        st.session_state.portfolio.append({
            "ticker": p_ticker,
            "shares": float(p_shares),
            "buy_price": float(p_price)
        })
        st.success(f"✅ {p_ticker} ajouté!")
        st.rerun()
st.markdown("---")

# Portfolio anzeigen
if not st.session_state.portfolio:
    st.info(t("portfolio_empty", lang))
else:
    portfolio_rows = []
    total_value    = 0
    total_cost     = 0

    for item in st.session_state.portfolio:
        try:
            s = yf.Ticker(item["ticker"])
            price = s.history(period="1d")["Close"].iloc[-1]
        except Exception:
            price = item["buy_price"]

        value    = price * item["shares"]
        cost     = item["buy_price"] * item["shares"]
        profit   = value - cost
        ret_pct  = ((price - item["buy_price"]) / item["buy_price"]) * 100

        total_value += value
        total_cost  += cost

        portfolio_rows.append({
            t("portfolio_stock",   lang): item["ticker"],
            t("portfolio_shares",  lang): item["shares"],
            t("portfolio_current", lang): f"{price:.2f}",
            t("portfolio_value",   lang): f"{value:.2f}",
            t("portfolio_profit",  lang): f"{profit:+.2f}",
            t("portfolio_return",  lang): f"{ret_pct:+.1f}%"
        })

    import pandas as pd
    port_df = pd.DataFrame(portfolio_rows)
    st.dataframe(port_df, hide_index=True, width='stretch')

    # Totals
    total_profit = total_value - total_cost
    total_ret    = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric(t("portfolio_total",  lang), f"{total_value:,.2f} USD")
    c2.metric(t("portfolio_profit", lang), f"{total_profit:+,.2f} USD")
    c3.metric(t("portfolio_return", lang), f"{total_ret:+.1f}%")

    # Export CSV
    st.markdown(f"#### {t('export_title', lang)}")
    csv = port_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=t("export_csv", lang),
        data=csv,
        file_name=f"portfolio_{ticker}.csv",
        mime="text/csv"
    )

    if st.button(t("portfolio_clear", lang)):
        st.session_state.portfolio = []
        st.rerun()

# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<div style="text-align:center;color:#4a4f6a;font-size:12px;padding:10px;">{t("disclaimer", lang)}</div>',
    unsafe_allow_html=True
)
