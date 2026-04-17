"""
IoT Energy Monitoring System - FastAPI Server
Complete REST API with Background Scheduling and Configuration
✅ ALL FILE OPERATIONS PROTECTED WITH FileLock
✅ ALL SETTINGS FULLY FUNCTIONAL
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from pdf_export import pdf_router
import pandas as pd
import json
from filelock import FileLock

# ─────────────────────────────────────────────────────────────
# APP INITIALIZATION
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="IoT Energy Monitoring API",
    description="Real-time energy consumption monitoring with anomaly detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

scheduler = BackgroundScheduler()
scheduler_running = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_router)

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
FRONTEND_DIR = BASE_DIR / "frontend"

BUFFER_FILE = DATA_DIR / "buffer.csv"
ALERTS_FILE = DATA_DIR / "alerts.json"
BASELINE_FILE = DATA_DIR / "baseline.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# Static assets
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR / "static")),
    name="static"
)

# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────

from enum import Enum

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    FALSE_POSITIVE = "false_positive"
    TRUE_POSITIVE = "true_positive"
    DISMISSED = "dismissed"

class SettingsUpdate(BaseModel):
    detection_frequency_hours: Optional[float] = None
    buffer_hours: Optional[int] = None
    sample_rate_seconds: Optional[int] = None
    model_sensitivity: Optional[float] = None  # Replaces unused settings
    notification_enabled: Optional[bool] = None

class AlertCreate(BaseModel):
    timestamp: str
    power_kw: float
    baseline_kw: float
    deviation_percent: float
    alert_type: str
    severity: Optional[AlertSeverity] = AlertSeverity.MEDIUM
    status: Optional[AlertStatus] = AlertStatus.ACTIVE
    user_feedback: Optional[str] = None
    baseline_type: Optional[str] = None  
    if_score: Optional[float] = None      
    lstm_error: Optional[float] = None    

# ─────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS WITH FileLock PROTECTION
# ─────────────────────────────────────────────────────────────

def load_json_file(path: Path, default: dict):
    """Load JSON file with lock protection"""
    if path.exists():
        lock = FileLock(str(path) + ".lock")
        try:
            with lock:
                return json.loads(path.read_text())
        except json.JSONDecodeError:
            return default
    return default


def save_json_file(path: Path, data: dict):
    """Save JSON file with lock protection"""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(path) + ".lock")
    with lock:
        path.write_text(json.dumps(data, indent=2))


def calculate_baseline_from_buffer():
    """Calculate hourly baseline separated by weekday/weekend with lock protection"""
    if not BUFFER_FILE.exists():
        return None

    # Read buffer with lock
    lock = FileLock(str(BUFFER_FILE) + ".lock")
    with lock:
        df = pd.read_csv(BUFFER_FILE)
    
    # Parse timestamp to get day of week
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    
    # Separate weekday (Mon-Fri) and weekend (Sat-Sun)
    weekday_df = df[df['day_of_week'].isin([0, 1, 2, 3, 4])]
    weekend_df = df[df['day_of_week'].isin([5, 6])]
    
    # Calculate overall hourly baselines first (as fallback)
    all_hourly = df.groupby("hour")["power_kw"].agg(["mean", "std", "count"])
    hourly_baseline_temp = {
        str(hour): {
            "mean": float(row["mean"]),
            "std": float(row["std"]) if row["count"] > 1 else 0.0,
            "count": int(row["count"]),
        }
        for hour, row in all_hourly.iterrows()
    }
    
    # Calculate hourly baselines for weekdays
    weekday_hourly = weekday_df.groupby("hour")["power_kw"].agg(["mean", "std", "count"])
    weekday_baseline_temp = {
        str(hour): {
            "mean": float(row["mean"]),
            "std": float(row["std"]) if row["count"] > 1 else 0.0,
            "count": int(row["count"]),
        }
        for hour, row in weekday_hourly.iterrows()
    }
    
    # Calculate hourly baselines for weekends
    weekend_hourly = weekend_df.groupby("hour")["power_kw"].agg(["mean", "std", "count"])
    weekend_baseline_temp = {
        str(hour): {
            "mean": float(row["mean"]),
            "std": float(row["std"]) if row["count"] > 1 else 0.0,
            "count": int(row["count"]),
        }
        for hour, row in weekend_hourly.iterrows()
    }
    
    # Ensure all 24 hours exist in all three baselines
    default_hour = {"mean": 0.0, "std": 0.0, "count": 0}
    
    hourly_baseline = {}
    weekday_baseline = {}
    weekend_baseline = {}
    
    for hour in range(24):
        hour_str = str(hour)
        
        hourly_baseline[hour_str] = hourly_baseline_temp.get(hour_str, default_hour)
        
        if hour_str in weekday_baseline_temp:
            weekday_baseline[hour_str] = weekday_baseline_temp[hour_str]
        elif hour_str in hourly_baseline_temp:
            weekday_baseline[hour_str] = hourly_baseline_temp[hour_str]
        else:
            weekday_baseline[hour_str] = default_hour
        
        if hour_str in weekend_baseline_temp:
            weekend_baseline[hour_str] = weekend_baseline_temp[hour_str]
        elif hour_str in hourly_baseline_temp:
            weekend_baseline[hour_str] = hourly_baseline_temp[hour_str]
        else:
            weekend_baseline[hour_str] = default_hour
    
    baseline = {
        "hourly_baseline": hourly_baseline,
        "weekday_baseline": weekday_baseline,
        "weekend_baseline": weekend_baseline,
        "last_calculated": datetime.now().isoformat(),
        "sample_size": len(df),
        "weekday_samples": len(weekday_df),
        "weekend_samples": len(weekend_df),
    }
    
    save_json_file(BASELINE_FILE, baseline)
    return baseline


def calculate_severity(deviation_percent: float) -> str:
    """Calculate severity based on deviation from baseline"""
    dev = abs(deviation_percent)
    if dev > 50:
        return "critical"
    elif dev > 30:
        return "high"
    elif dev > 15:
        return "medium"
    else:
        return "low"


def log_feedback_for_retraining(alert: dict):
    """Store user feedback with lock protection"""
    feedback_file = DATA_DIR / "feedback.json"
    lock = FileLock(str(feedback_file) + ".lock")
    
    with lock:
        if feedback_file.exists():
            feedback_data = json.loads(feedback_file.read_text())
        else:
            feedback_data = {"feedback": []}
        
        feedback_data["feedback"].append({
            "alert_id": alert["id"],
            "timestamp": alert["timestamp"],
            "feedback": alert.get("user_feedback"),
            "power_kw": alert["power_kw"],
            "baseline_kw": alert["baseline_kw"],
            "deviation_percent": alert["deviation_percent"],
            "feedback_recorded_at": datetime.now().isoformat()
        })
        
        feedback_file.write_text(json.dumps(feedback_data, indent=2))

# ─────────────────────────────────────────────────────────────
# FRONTEND ROUTES (HTML)
# ─────────────────────────────────────────────────────────────

def serve_html(filename: str):
    path = FRONTEND_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return path.read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return serve_html("index.html")


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page():
    return serve_html("analytics.html")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    return serve_html("settings.html")


@app.get("/system", response_class=HTMLResponse)
async def system_page():
    return serve_html("system.html")

# ─────────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/current")
async def current():
    if not BUFFER_FILE.exists():
        raise HTTPException(404, "No data available")

    lock = FileLock(str(BUFFER_FILE) + ".lock")
    with lock:
        df = pd.read_csv(BUFFER_FILE)
    
    latest = df.iloc[-1].to_dict()

    baseline = load_json_file(BASELINE_FILE, {}).get("hourly_baseline", {})
    hour = str(int(latest["hour"]))
    baseline_kw = baseline.get(hour, {}).get("mean")

    return {
        **latest,
        "baseline_kw": baseline_kw,
        "buffer_size": len(df)
    }


@app.get("/api/history")
async def history(hours: int = Query(24, ge=1, le=168)):
    lock = FileLock(str(BUFFER_FILE) + ".lock")
    with lock:
        df = pd.read_csv(BUFFER_FILE)
    
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    cutoff = datetime.now() - timedelta(hours=hours)
    df = df[df["timestamp"] >= cutoff]

    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    return {
        "count": len(df),
        "data": df.to_dict("records")
    }


@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    alerts = load_json_file(ALERTS_FILE, {"alerts": []})
    return alerts["alerts"][-limit:][::-1]


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Mark alert as acknowledged by user"""
    alerts_data = load_json_file(ALERTS_FILE, {"alerts": [], "total_count": 0})
    
    for alert in alerts_data["alerts"]:
        if alert["id"] == alert_id:
            alert["status"] = "acknowledged"
            alert["acknowledged_at"] = datetime.now().isoformat()
            alerts_data["last_updated"] = datetime.now().isoformat()
            save_json_file(ALERTS_FILE, alerts_data)
            return alert
    
    raise HTTPException(404, "Alert not found")


@app.post("/api/alerts/{alert_id}/feedback")
async def set_alert_feedback(alert_id: int, feedback: dict):
    """
    User marks alert as false positive or true positive
    This data feeds into model retraining
    
    Expected body: {"feedback": "false_positive" or "true_positive"}
    """
    alerts_data = load_json_file(ALERTS_FILE, {"alerts": [], "total_count": 0})
    
    for alert in alerts_data["alerts"]:
        if alert["id"] == alert_id:
            alert["status"] = feedback.get("feedback")
            alert["user_feedback"] = feedback.get("feedback")
            alert["feedback_at"] = datetime.now().isoformat()
            alerts_data["last_updated"] = datetime.now().isoformat()
            save_json_file(ALERTS_FILE, alerts_data)
            
            log_feedback_for_retraining(alert)
            
            return alert
    
    raise HTTPException(404, "Alert not found")


@app.get("/api/alerts/filter")
async def filter_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None
):
    """
    Filter alerts by multiple criteria
    Example: /api/alerts/filter?status=active&severity=high&start_date=2026-02-01
    """
    alerts_data = load_json_file(ALERTS_FILE, {"alerts": [], "total_count": 0})
    alerts = alerts_data["alerts"]

    def parse_dt(value: Optional[str]):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    
    start_dt = parse_dt(start_date)
    end_dt = parse_dt(end_date)
    
    if status:
        alerts = [a for a in alerts if a.get("status") == status]
    
    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]

    if start_dt or end_dt:
        filtered = []
        for a in alerts:
            ts = parse_dt(a.get("timestamp")) or parse_dt(a.get("created_at"))
            if not ts:
                continue
            if start_dt and ts < start_dt:
                continue
            if end_dt and ts > end_dt:
                continue
            filtered.append(a)
        alerts = filtered
    
    if search:
        alerts = [a for a in alerts if search.lower() in a.get("timestamp", "").lower()]
    
    return sorted(alerts, key=lambda x: x.get("created_at", ""), reverse=True)


@app.post("/api/alerts")
async def create_alert(alert: AlertCreate):
    data = load_json_file(ALERTS_FILE, {"alerts": [], "total_count": 0})

    try:
        datetime.fromisoformat(alert.timestamp)
    except Exception:
        raise HTTPException(422, "Invalid timestamp format. Use ISO 8601.")

    severity = alert.severity
    if not severity:
        severity = calculate_severity(alert.deviation_percent)
    
    status = alert.status or AlertStatus.ACTIVE

    entry = {
        "id": data["total_count"] + 1,
        **alert.dict(exclude={"severity", "status"}),
        "severity": severity,
        "status": status,
        "created_at": datetime.now().isoformat()
    }

    data["alerts"].append(entry)
    data["total_count"] += 1
    data["last_updated"] = datetime.now().isoformat()

    save_json_file(ALERTS_FILE, data)
    return entry


@app.delete("/api/alerts")
async def clear_alerts():
    """Clear all alert history"""
    data = load_json_file(ALERTS_FILE, {"alerts": [], "total_count": 0})
    
    cleared_count = len(data["alerts"])
    data["alerts"] = []
    data["total_count"] = 0
    data["last_updated"] = datetime.now().isoformat()
    
    save_json_file(ALERTS_FILE, data)
    
    return {
        "message": "Alert history cleared successfully",
        "cleared_count": cleared_count,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/baseline")
async def baseline(recalculate: bool = False):
    print(f"📊 Baseline endpoint called - recalculate={recalculate}")
    
    if recalculate or not BASELINE_FILE.exists():
        print("📊 Starting baseline calculation...")
        try:
            baseline = calculate_baseline_from_buffer()
            print(f"✅ Baseline calculated successfully")
            
            if not baseline:
                print("❌ Baseline is None - no buffer data")
                raise HTTPException(404, "No buffer data")
            
            print(f"📊 Baseline has {len(baseline.get('hourly_baseline', {}))} hours")
            return baseline
        except Exception as e:
            print(f"❌ Error calculating baseline: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(500, f"Baseline calculation error: {str(e)}")

    print("📊 Loading existing baseline file")
    result = load_json_file(BASELINE_FILE, {})
    print(f"📊 Returning baseline with {len(result.get('hourly_baseline', {}))} hours")
    return result


@app.get("/api/statistics")
async def statistics():
    lock = FileLock(str(BUFFER_FILE) + ".lock")
    with lock:
        df = pd.read_csv(BUFFER_FILE)
    
    spike_count = int(df["is_spike"].sum()) if "is_spike" in df.columns else 0
    alerts_data = load_json_file(ALERTS_FILE, {"alerts": [], "total_count": 0})
    alert_count = len(alerts_data["alerts"])

    return {
        "average_kw": float(df["power_kw"].mean()),
        "max_kw": float(df["power_kw"].max()),
        "min_kw": float(df["power_kw"].min()),
        "alerts": alert_count,
        "spikes": spike_count,
        "total_readings": len(df),
    }


@app.get("/api/analytics")
async def analytics():
    """Get advanced analytics including weekday/weekend patterns"""
    if not BUFFER_FILE.exists():
        raise HTTPException(status_code=404, detail="No data available")
    
    try:
        lock = FileLock(str(BUFFER_FILE) + ".lock")
        with lock:
            df = pd.read_csv(BUFFER_FILE)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        hourly_pattern = df.groupby('hour')['power_kw'].agg(['mean', 'std', 'count']).to_dict('index')
        hourly_pattern_formatted = {
            str(hour): {
                "mean": float(stats['mean']),
                "std": float(stats['std']),
                "count": int(stats['count'])
            }
            for hour, stats in hourly_pattern.items()
        }
        
        weekday_data = df[df['is_weekend'] == 0]['power_kw']
        weekend_data = df[df['is_weekend'] == 1]['power_kw']
        
        weekday_vs_weekend = {
            "weekday": {
                "mean": float(weekday_data.mean()) if len(weekday_data) > 0 else 0,
                "max": float(weekday_data.max()) if len(weekday_data) > 0 else 0,
                "min": float(weekday_data.min()) if len(weekday_data) > 0 else 0,
                "count": len(weekday_data)
            },
            "weekend": {
                "mean": float(weekend_data.mean()) if len(weekend_data) > 0 else 0,
                "max": float(weekend_data.max()) if len(weekend_data) > 0 else 0,
                "min": float(weekend_data.min()) if len(weekend_data) > 0 else 0,
                "count": len(weekend_data)
            }
        }
        
        df['date'] = df['timestamp'].dt.date
        daily_consumption = df.groupby('date')['power_kw'].agg(['mean', 'max', 'min']).reset_index()
        daily_consumption['date'] = daily_consumption['date'].astype(str)
        
        daily_list = [
            {
                "date": row['date'],
                "average_kw": float(row['mean']),
                "max_kw": float(row['max']),
                "min_kw": float(row['min'])
            }
            for _, row in daily_consumption.iterrows()
        ]
        
        today = datetime.now().date()
        today_data = df[df['timestamp'].dt.date == today]
        
        today_stats = {
            "total_readings": len(today_data),
            "mean_power": float(today_data['power_kw'].mean()) if len(today_data) > 0 else 0,
            "max_power": float(today_data['power_kw'].max()) if len(today_data) > 0 else 0,
            "spikes": int(today_data['is_spike'].sum()) if 'is_spike' in today_data.columns else 0
        }
        
        today_alerts = 0
        if ALERTS_FILE.exists():
            alerts_data = load_json_file(ALERTS_FILE, {"alerts": [], "total_count": 0})
            for alert in alerts_data.get('alerts', []):
                try:
                    alert_date = datetime.fromisoformat(alert['created_at']).date()
                    if alert_date == today:
                        today_alerts += 1
                except:
                    pass
        
        today_stats['alerts'] = today_alerts
        
        now = datetime.now()
        last_24h = df[df['timestamp'] >= (now - timedelta(hours=24))]
        prev_24h = df[(df['timestamp'] >= (now - timedelta(hours=48))) & 
                      (df['timestamp'] < (now - timedelta(hours=24)))]
        
        trend = {
            "current_avg": float(last_24h['power_kw'].mean()) if len(last_24h) > 0 else 0,
            "previous_avg": float(prev_24h['power_kw'].mean()) if len(prev_24h) > 0 else 0,
            "change_percent": 0.0
        }
        
        if trend['previous_avg'] > 0:
            trend['change_percent'] = ((trend['current_avg'] - trend['previous_avg']) / 
                                      trend['previous_avg'] * 100)
        
        return {
            "hourly_pattern": hourly_pattern_formatted,
            "weekday_vs_weekend": weekday_vs_weekend,
            "daily_consumption": daily_list,
            "today": today_stats,
            "trend": trend,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@app.get("/api/settings")
async def get_settings():
    return load_json_file(SETTINGS_FILE, {})


@app.post("/api/settings")
async def update_settings(update: SettingsUpdate):
    settings = load_json_file(SETTINGS_FILE, {})
    settings.update(update.dict(exclude_unset=True))
    settings["last_updated"] = datetime.now().isoformat()

    save_json_file(SETTINGS_FILE, settings)
    
    # ✅ NEW: Notify if scheduler needs restart for detection_frequency_hours
    if update.detection_frequency_hours is not None:
        return {
            **settings,
            "warning": "Detection frequency changed. Restart server to apply changes."
        }
    
    return settings


@app.post("/api/run-detection")
async def run_detection():
    from anomaly_detector import AnomalyDetector

    detector = AnomalyDetector(
        data_dir=str(DATA_DIR),
        model_dir=str(BASE_DIR / "models")
    )

    return detector.run_detection()


@app.get("/api/scheduler/status")
async def scheduler_status():
    """Get status of background scheduler"""
    jobs = []
    
    if scheduler_running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name or job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })
    
    return {
        "running": scheduler_running,
        "jobs": jobs,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/retrain")
async def trigger_retraining():
    """Trigger model retraining with user feedback (completes ML feedback loop)"""
    from retraining_pipeline import RetrainingPipeline
    
    # ✅ NEW: Pass model_sensitivity from settings to retraining
    settings = load_json_file(SETTINGS_FILE, {})
    model_sensitivity = settings.get("model_sensitivity", 0.03)
    
    pipeline = RetrainingPipeline(
        data_dir=str(DATA_DIR),
        model_dir=str(BASE_DIR / "models")
    )
    
    # Apply sensitivity setting
    pipeline.trainer.contamination = model_sensitivity
    
    result = pipeline.retrain_from_feedback()
    return result

# ─────────────────────────────────────────────────────────────
# STARTUP / SHUTDOWN
# ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global scheduler_running
    
    from retraining_pipeline import RetrainingPipeline

    DATA_DIR.mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)
    (BASE_DIR / "models").mkdir(exist_ok=True)

    if not ALERTS_FILE.exists():
        save_json_file(ALERTS_FILE, {"alerts": [], "total_count": 0})

    if not SETTINGS_FILE.exists():
        save_json_file(SETTINGS_FILE, {
            "detection_frequency_hours": 1.0,
            "buffer_hours": 24,
            "sample_rate_seconds": 60,
            "model_sensitivity": 0.03,  # ✅ NEW: Replaces unused settings
            "notification_enabled": True
        })

    models_ok = (
        (BASE_DIR / "models/isolation_forest.pkl").exists() and
        (BASE_DIR / "models/lstm_autoencoder.h5").exists()
    )

    if models_ok:
        from anomaly_detector import AnomalyDetector
        
        def run_scheduled_detection():
            """Background job to run anomaly detection"""
            try:
                detector = AnomalyDetector(
                    data_dir=str(DATA_DIR),
                    model_dir=str(BASE_DIR / "models")
                )
                result = detector.run_detection()
                print(f"[SCHEDULER] Detection complete: {result.get('alerts', 0)} alerts found")
            except Exception as e:
                print(f"[SCHEDULER] Detection error: {e}")
        
        def run_scheduled_retraining():
            """Background job to retrain models with user feedback"""
            try:
                # ✅ NEW: Apply model_sensitivity from settings
                settings = load_json_file(SETTINGS_FILE, {})
                model_sensitivity = settings.get("model_sensitivity", 0.03)
                
                pipeline = RetrainingPipeline(
                    data_dir=str(DATA_DIR),
                    model_dir=str(BASE_DIR / "models")
                )
                
                pipeline.trainer.contamination = model_sensitivity
                
                result = pipeline.retrain_from_feedback()
                print(f"[SCHEDULER] Retraining result: {result.get('status')}")
            except Exception as e:
                print(f"[SCHEDULER] Retraining error: {e}")
        
        settings = load_json_file(SETTINGS_FILE, {})
        detection_hours = settings.get("detection_frequency_hours", 1.0)
        
        scheduler.add_job(
            func=run_scheduled_detection,
            trigger=IntervalTrigger(hours=detection_hours),
            id="anomaly_detection",
            name="Anomaly Detection"
        )
        
        scheduler.add_job(
            func=run_scheduled_retraining,
            trigger=CronTrigger(hour=3, minute=0),
            id="model_retraining",
            name="Daily Model Retraining"
        )
        
        scheduler.start()
        scheduler_running = True
        print(f"✅ Scheduler started - Running detection every {detection_hours} hour(s)")
        print(f"✅ Scheduler started - Running retraining daily at 3:00 AM")
        print(f"✅ Model sensitivity: {settings.get('model_sensitivity', 0.03)}")
    else:
        print("⚠️ ML models not found - scheduler disabled")


@app.on_event("shutdown")
async def shutdown():
    if scheduler_running:
        scheduler.shutdown(wait=False)