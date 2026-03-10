"""
LSTM Neural Network für Aktienkurs-Vorhersage
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import warnings
import traceback
warnings.filterwarnings("ignore")


def create_sequences(data, seq_len):
    seq_len = int(seq_len)
    X, y = [], []
    for i in range(seq_len, len(data)):
        X.append(data[i - seq_len:i])
        y.append(data[i, 0])
    return np.array(X), np.array(y)


def build_lstm_model(seq_len, n_features):
    seq_len    = int(seq_len)
    n_features = int(n_features)
    try:
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.optimizers import Adam
    except ImportError:
        from keras.models import Sequential
        from keras.layers import LSTM, Dense, Dropout
        from keras.optimizers import Adam

    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=(seq_len, n_features)),
        Dropout(0.2),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        Dense(32, activation="relu"),
        Dense(1)
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss="mse")
    return model


def predict_lstm(df, forecast_days=30, seq_len=60, epochs=30):

    forecast_days = int(forecast_days)
    seq_len       = int(seq_len)
    epochs        = int(epochs)

    try:
        # Schritt 1: Features
        feature_cols = [c for c in ["Close", "Volume", "High", "Low"] if c in df.columns]
        data_raw = df[feature_cols].dropna().values.astype(float)

        # Automatisch seq_len reduzieren wenn zu wenig Daten
        n = len(data_raw)
        if n < seq_len + 20:
            seq_len = max(5, n - 20)  # mindestens 5 Tage Sequenz

        if n < 25:
            return {"error": f"Zu wenig Daten ({n} Tage). Bitte mindestens 3 Monate Zeitraum wählen."}

        # Schritt 2: Normalisierung
        scaler = MinMaxScaler(feature_range=(0, 1))
        data_scaled = scaler.fit_transform(data_raw)

        # Schritt 3: Sequenzen
        split = int(len(data_scaled) * 0.8)
        X_train, y_train = create_sequences(data_scaled[:split], seq_len)
        X_test,  y_test  = create_sequences(data_scaled[split - seq_len:], seq_len)

        # Schritt 4: Training
        model = build_lstm_model(seq_len, int(X_train.shape[2]))
        history = model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=32,
            validation_split=0.1,
            verbose=0
        )

        # Schritt 5: Genauigkeit
        y_pred_scaled = model.predict(X_test, verbose=0)
        dummy = np.zeros((len(y_pred_scaled), data_raw.shape[1]))
        dummy[:, 0] = y_pred_scaled.flatten()
        y_pred_test = scaler.inverse_transform(dummy)[:, 0]

        dummy2 = np.zeros((len(y_test), data_raw.shape[1]))
        dummy2[:, 0] = y_test
        y_true_test = scaler.inverse_transform(dummy2)[:, 0]

        mape     = float(np.mean(np.abs((y_true_test - y_pred_test) / (y_true_test + 1e-8))) * 100)
        accuracy = float(max(0.0, 100.0 - mape))
        std_err  = float(np.std(y_true_test - y_pred_test))

        # Schritt 6: Zukunft
        last_seq = data_scaled[-seq_len:].copy()
        future_preds = []
        for _ in range(forecast_days):
            x_in = last_seq.reshape(1, seq_len, data_raw.shape[1])
            p = float(model.predict(x_in, verbose=0)[0, 0])
            next_row = last_seq[-1].copy()
            next_row[0] = p
            last_seq = np.vstack([last_seq[1:], next_row])
            future_preds.append(p)

        future_arr = np.zeros((forecast_days, data_raw.shape[1]))
        future_arr[:, 0] = future_preds
        future_prices = scaler.inverse_transform(future_arr)[:, 0]

        conf_upper = (future_prices + 1.5 * std_err).tolist()
        conf_lower = (future_prices - 1.5 * std_err).tolist()

        # Schritt 7: Datum - alles als reiner String YYYY-MM-DD
        last_date_str = str(df.index[-1])[:10]
        last_date = pd.Timestamp(last_date_str)
        future_dates = pd.bdate_range(
            start=last_date + pd.Timedelta(days=1),
            periods=forecast_days
        )
        future_dates_str = [d.strftime("%Y-%m-%d") for d in future_dates]
        hist_dates_str   = [pd.Timestamp(str(x)[:10]).strftime("%Y-%m-%d") for x in df.index[-120:]]

        return {
            "dates_hist" : hist_dates_str,
            "close_hist" : [float(x) for x in df["Close"].values[-120:]],
            "dates_pred" : future_dates_str,
            "close_pred" : [float(x) for x in future_prices],
            "conf_upper" : conf_upper,
            "conf_lower" : conf_lower,
            "train_loss" : [float(x) for x in history.history["loss"]],
            "val_loss"   : [float(x) for x in history.history.get("val_loss", [])],
            "accuracy"   : round(accuracy, 1),
            "mape"       : round(mape, 2),
            "std_err"    : round(std_err, 2),
        }

    except Exception as e:
        # Zeigt GENAU welche Zeile den Fehler verursacht
        full_trace = traceback.format_exc()
        return {"error": f"{str(e)}\n\n--- DETAILS (bitte kopieren) ---\n{full_trace}"}
