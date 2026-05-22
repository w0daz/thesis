# IoT Energy Monitoring System

A real-time energy monitoring and anomaly detection system built with machine learning. This simulation environment demonstrates intelligent power consumption analysis using FastAPI, TensorFlow, and interactive visualizations.

[![Python Version](https://img.shields.io/badge/python-3.11.6-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.8-009688.svg)](https://fastapi.tiangolo.com)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.18.0-FF6F00.svg)](https://www.tensorflow.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Overview

This project simulates a complete IoT energy monitoring system that tracks household power consumption, detects anomalies using machine learning (Isolation Forest + LSTM Autoencoder), and provides real-time visualization through a web-based dashboard. Designed for thesis demonstration and scalable to real Raspberry Pi hardware deployment.

### Key Features

- **Real-time Monitoring**: Live power consumption tracking with 30-second update intervals
- **ML-Powered Anomaly Detection**: Hybrid detection using Isolation Forest and LSTM Autoencoder
- **Interactive Dashboard**: Chart.js-based visualizations with 24-hour baseline comparison
- **REST API**: FastAPI backend with auto-generated documentation
- **Alert System**: Automatic notification for consumption spikes and anomalies
- **Configurable**: Adjustable sampling rates, thresholds, and detection parameters
- **Production-Ready**: Industry-standard architecture suitable for real-world deployment

## Architecture

```
energy_monitoring_system/
│
├── backend/
│   ├── main.py                    # FastAPI application entry point
│   ├── sensor_simulator.py        # ACS712 sensor data simulation
│   ├── anomaly_detector.py        # ML detection pipeline
│   ├── data_buffer.py             # Rolling 24-hour data buffer
│   └── models/
│       ├── isolation_forest.pkl   # Pre-trained Isolation Forest
│       └── lstm_autoencoder.h5    # Pre-trained LSTM model
│
├── frontend/
│   ├── index.html                 # Main dashboard interface
│   ├── static/
│   │   ├── css/
│   │   │   └── dashboard.css      # Dashboard styling
│   │   └── js/
│   │       ├── chart-config.js    # Chart.js configuration
│   │       └── api-client.js      # API communication layer
│   └── assets/
│       └── images/                # UI assets
│
├── data/
│   ├── buffer.csv                 # Current 24-hour readings
│   ├── alerts.json                # Alert history
│   └── baseline.json              # Learned consumption patterns
│
├── config/
│   └── settings.py                # System configuration
│
├── tests/
│   └── test_api.py                # API endpoint tests
│
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── .env                           # Environment variables
```

## Technology Stack

### Backend
- **FastAPI** (0.115.8) - High-performance async web framework
- **Uvicorn** - ASGI server for production deployment
- **Pydantic** - Data validation and settings management
- **APScheduler** - Background task automation

### Machine Learning
- **TensorFlow** (2.18.0) - Deep learning framework for LSTM
- **scikit-learn** (1.6.1) - Isolation Forest implementation
- **NumPy** (1.26.4) - Numerical computing
- **Pandas** (2.2.3) - Data manipulation and analysis

### Frontend
- **Chart.js** - Lightweight, real-time charting library
- **Vanilla JavaScript** - No framework dependencies
- **Responsive CSS** - Mobile-friendly dashboard design

### Visualization & Analysis
- **Matplotlib** (3.10.0) - Statistical plotting
- **Seaborn** (0.13.2) - Advanced visualizations

## Installation

### Prerequisites

- Python 3.11.6 or higher
- pip package manager
- (Optional) Virtual environment tool

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/energy-monitoring-system.git
   cd energy-monitoring-system
   ```

2. **Create and activate virtual environment** (recommended)
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize data directories**
   ```bash
   mkdir -p data backend/models
   ```

## Usage

### Running the Application

**Development Mode:**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Production Mode:**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Access the dashboard at: `http://localhost:8000`

### API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve dashboard HTML |
| GET | `/api/current` | Latest power reading |
| GET | `/api/history?hours=24` | Historical data |
| GET | `/api/alerts` | Recent alerts |
| GET | `/api/baseline` | 24-hour baseline pattern |
| POST | `/api/settings` | Update alert thresholds |
| GET | `/api/run-detection` | Manual anomaly detection trigger |

## System Workflow

```
[Sensor Simulator] --1 min--> [buffer.csv] --1 hour--> [Anomaly Detector]
                                    ↓                          ↓
                              [FastAPI Server] <-------- [alerts.json]
                                    ↓
                              [Dashboard] (Chart.js updates every 30s)
```

1. **Data Generation**: Sensor simulator generates realistic power readings every minute
2. **Storage**: Readings stored in rolling 24-hour CSV buffer
3. **Detection**: ML models analyze data hourly for anomalies
4. **Alerts**: Anomalies saved to alerts.json
5. **Visualization**: Dashboard polls API and updates charts in real-time

## Configuration

Edit `.env` file to customize system behavior:

```env
# Sensor Configuration
SAMPLING_RATE=60              # Seconds between readings
POWER_MIN=0.5                 # Minimum power (kW)
POWER_MAX=5.0                 # Maximum power (kW)

# Detection Settings
DETECTION_INTERVAL=3600       # Seconds between ML runs
ALERT_THRESHOLD_PERCENTILE=95 # Anomaly threshold
SPIKE_PROBABILITY=0.03        # Chance of random spike

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

## Deployment Options

### Option 1: Local Testing
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Access: `http://localhost:8000`

### Option 2: Public Demo (Ngrok)
```bash
# Terminal 1: Start server
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Expose via ngrok
ngrok http 8000
```
Access: `https://abc123.ngrok.io` (shareable public URL)

### Option 3: Raspberry Pi Deployment
```bash
# Same commands as local, runs on RPi
# Access from any device on WiFi: http://192.168.1.100:8000
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Test specific endpoint
pytest tests/test_api.py::test_current_reading
```

## Development Roadmap

### Completed
- ✅ FastAPI backend with REST API
- ✅ Sensor data simulation
- ✅ ML anomaly detection (IF + LSTM)
- ✅ Real-time dashboard with Chart.js
- ✅ Alert system and notifications
- ✅ Background task automation

### Planned
- ⏳ PostgreSQL integration for historical data
- ⏳ User authentication and multi-user support
- ⏳ Mobile app (React Native)
- ⏳ Integration with actual ACS712 sensors
- ⏳ Email/SMS alert notifications
- ⏳ Energy cost estimation

## Performance

- **API Response Time**: < 50ms average
- **Chart Update Interval**: 30 seconds
- **Detection Frequency**: 1 hour (configurable)
- **Data Retention**: Rolling 24 hours (expandable)
- **Concurrent Users**: Supports 100+ with default configuration

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Change port in command
uvicorn backend.main:app --port 8001
```

**ModuleNotFoundError:**
```bash
# Ensure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

**CORS errors in browser:**
```python
# Verify CORS middleware in main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FastAPI framework by Sebastián Ramírez
- Chart.js for excellent real-time charting capabilities
- TensorFlow team for robust ML infrastructure
- Inspired by real-world IoT energy monitoring systems

## Citation

If you use this project in academic research, please cite:

```bibtex
@misc{iot-energy-monitoring,
  author = {Gabriel Ogungbade},
  title = {IoT Energy Monitoring System with ML-Based Anomaly Detection},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/w0daz/thesis}
}

---

**Built with ❤️ for sustainable energy monitoring**
