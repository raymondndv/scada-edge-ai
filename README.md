# SCADA Edge AI – Phân tích dữ liệu SCADA thời gian thực bằng AI để đưa ra cảnh báo sớm

Đồ án tốt nghiệp – Trường Đại học Bách Khoa, ĐHQG-HCM, Khoa Khoa học và Kỹ thuật Máy tính (Ngành Kỹ thuật Máy tính).

- **GVHD:** TS. Võ Tuấn Bình
- **Nhóm thực hiện:** Nguyễn Đại Vinh (2053589), Phạm Viết Huy (2211269), Nguyễn Thành Đạt (2210700)
- **Tài liệu:** [Báo cáo](docs/report-HK253-DATN-056.pdf) · [Slide bảo vệ](docs/slide.pdf)

## Tổng quan

Hệ thống đưa suy luận AI về sát nguồn dữ liệu (Edge) thay vì đẩy toàn bộ dữ liệu thô lên Cloud:

```
Dữ liệu SCADA (phát lại 1 Hz)
        │
        ▼
AI Exporter (XGBoost + residual)  ──►  InfluxDB v2  ──►  Grafana (Dashboard + Alert + Email)
   Orange Pi 5 Plus (ARM64)          (WAL + TSM)        (FIRING / RESOLVED qua SMTP)
```

- **Dự báo công suất kỳ vọng** bằng XGBoost với 7 đặc trưng: tốc độ gió, đường cong công suất lý thuyết, hướng gió, mã hóa chu kỳ giờ/tháng (sin–cos).
- **Phát hiện bất thường** theo quy tắc 3σ: `τ = μ_r + 3σ_r = 1942.07 kW`, với residual `r = |P_actual − P_predicted|`.
- **Chống báo động giả:** hysteresis (τ_on = 1942.07 kW, τ_off = 1700 kW) và Pending 30 s.
- **Triển khai:** 3 container (AI Exporter, InfluxDB, Grafana) bằng Docker Compose, có giới hạn CPU/RAM.

### Kết quả chính

| Chỉ số | Giá trị |
|---|---|
| MAE (4.457 mẫu test) | 344.21 kW |
| RMSE (test) | 634.11 kW |
| Suy luận / mẫu trên Orange Pi 5 Plus | 1.15 ms |
| Độ trễ cảnh báo đầu cuối | 36.65 s |
| Công suất tiêu thụ | 5–8.5 W |

## Cấu trúc thư mục

```
.
├── docs/
│   ├── report-HK253-DATN-056.pdf
│   └── slide.pdf
├── exporter/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── stream_exporter.py
│   ├── artifacts/        # config.json, xgboost_model.json, scaler.joblib
│   └── data/test.csv     # dữ liệu phát lại
├── docker-compose.yml
├── .env.example
└── README.md
```

## Chạy thử

Yêu cầu: Docker và Docker Compose (chạy được trên x86-64 và ARM64).

```bash
git clone <URL_REPO>
cd scada-edge-ai

cp .env.example .env
# Sửa .env: đặt mật khẩu, tạo token bằng:  openssl rand -base64 48

docker compose up -d --build
docker compose logs -f ai_exporter
```

- Grafana: http://localhost:3000
- InfluxDB: http://localhost:8086

Dashboard và Alert Rule của Grafana cần được cấu hình (datasource InfluxDB/Flux, query `turbine_status`, rule residual với τ_on/τ_off) hoặc import từ file export nếu có.

## Chạy exporter không dùng Docker

```bash
cd exporter
pip install -r requirements.txt
export INFLUX_TOKEN=<token>      # INFLUX_URL mặc định http://localhost:8086
python stream_exporter.py
```

## Dữ liệu

Dữ liệu SCADA tua-bin gió dạng chuỗi thời gian (Date/Time, LV ActivePower, Wind Speed, Theoretical Power Curve, Wind Direction). Repo chỉ kèm phần test để phát lại; hãy ghi rõ nguồn và giấy phép của bộ dữ liệu gốc ở đây.

## Hạn chế và hướng phát triển

Chưa kết nối trực tiếp PLC (mới phát lại dữ liệu lịch sử); thiếu pitch angle, trạng thái phanh, power setpoint; hướng tới Modbus TCP / OPC UA / MQTT, nhiều tua-bin và theo dõi data drift.

## Giấy phép

Chưa chọn – xem https://choosealicense.com (ví dụ MIT cho mã nguồn).
