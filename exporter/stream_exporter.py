"""AI Exporter: phát lại dữ liệu SCADA 1 Hz, dự báo công suất bằng XGBoost,
tính residual và ghi vào InfluxDB.

Cấu hình kết nối lấy từ biến môi trường (xem .env.example)."""
import json
import os
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR / "artifacts"
DATA_PATH = BASE_DIR / "data" / "test.csv"

# 1. CẤU HÌNH INFLUXDB (từ biến môi trường, không hard-code token)
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]
INFLUX_ORG = os.getenv("INFLUX_ORG", "scada_org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "turbine_metrics")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# 2. TẢI MÔ HÌNH VÀ TIỀN XỬ LÝ
model = xgb.XGBRegressor()
model.load_model(str(ARTIFACT_DIR / "xgboost_model.json"))
scaler = joblib.load(ARTIFACT_DIR / "scaler.joblib")

with open(ARTIFACT_DIR / "config.json", "r") as f:
    config = json.load(f)

threshold = config["anomaly_threshold"]
features = config["features"]

df_test = pd.read_csv(DATA_PATH).dropna()
df_test["Date/Time"] = pd.to_datetime(df_test["Date/Time"], format="%d %m %Y %H:%M")

hour = df_test["Date/Time"].dt.hour
minute = df_test["Date/Time"].dt.minute
df_test["Day_sin"] = np.sin(2 * np.pi * (hour * 60 + minute) / 1440)
df_test["Day_cos"] = np.cos(2 * np.pi * (hour * 60 + minute) / 1440)
df_test["Month_sin"] = np.sin(2 * np.pi * df_test["Date/Time"].dt.month / 12)
df_test["Month_cos"] = np.cos(2 * np.pi * df_test["Date/Time"].dt.month / 12)

print("🚀 Bắt đầu đẩy dữ liệu SCADA lên InfluxDB...")

# 3. VÒNG LẶP STREAMING (1 mẫu / giây)
for _, row in df_test.iterrows():
    t0 = time.perf_counter()

    actual_power = row["LV ActivePower (kW)"]
    wind_speed = row["Wind Speed (m/s)"]

    x_raw = row[features].to_frame().T
    x_scaled = scaler.transform(x_raw)
    pred_power = float(model.predict(x_scaled)[0])

    residual = float(abs(actual_power - pred_power))
    is_anomaly = 1 if residual > threshold else 0

    point = (
        Point("turbine_status")
        .tag("turbine_id", "T1")
        .field("wind_speed", float(wind_speed))
        .field("actual_power", float(actual_power))
        .field("predicted_power", float(pred_power))
        .field("residual", float(residual))
        .field("anomaly_flag", int(is_anomaly))
        .time(time.time_ns(), WritePrecision.NS)
    )

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    print(f"Đã gửi: Gió {wind_speed:5.1f}m/s | Lệch {residual:6.1f}kW | Cảnh báo: {is_anomaly}")

    # Điều tiết nhịp: Δt_sleep = max(0, 1.0 - Δt_proc)
    time.sleep(max(0.0, 1.0 - (time.perf_counter() - t0)))
