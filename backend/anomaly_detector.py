"""
IoT Energy Monitoring System - Anomaly Detector
Real-time spike detection using Isolation Forest + LSTM Autoencoder
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from filelock import FileLock
import pickle
import json
import tensorflow as tf
import requests

class AnomalyDetector:
    """Hybrid anomaly detection using IF + LSTM"""
    
    def __init__(self, data_dir="../data", model_dir="../models"):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        
        # Model paths
        self.if_model_path = self.model_dir / "isolation_forest.pkl"
        self.lstm_model_path = self.model_dir / "lstm_autoencoder.h5"
        self.if_scaler_path = self.model_dir / "if_scaler.pkl"
        self.lstm_scaler_path = self.model_dir / "scaler.pkl"
        self.metadata_path = self.model_dir / "model_metadata.json"
        self.alerts_path = self.data_dir / "alerts.json"
        self.detection_state_path = self.data_dir / "detection_state.json"
        
        # Load models
        self.if_model = None
        self.lstm_model = None
        self.if_scaler = None
        self.lstm_scaler = None
        self.metadata = None
        self.lstm_threshold = None
        self.sequence_length = 24
        
        self._load_models()
    
    def _load_models(self):
        """Load trained models"""
        print("📦 Loading anomaly detection models...")
        
        # Check if models exist
        if not all([
            self.if_model_path.exists(),
            self.lstm_model_path.exists(),
            self.if_scaler_path.exists(),
            self.lstm_scaler_path.exists()
        ]):
            raise FileNotFoundError(
                "Models not found. Run model_trainer.py first to train models."
            )
        
        # Load Isolation Forest
        with open(self.if_model_path, 'rb') as f:
            self.if_model = pickle.load(f)
        print("✓ Loaded Isolation Forest")
        
        # Load LSTM
        self.lstm_model = tf.keras.models.load_model(
            self.lstm_model_path,
            compile=False
        )
        print("✓ Loaded LSTM Autoencoder")
        
        # Load IF scaler (4 features)
        with open(self.if_scaler_path, 'rb') as f:
            self.if_scaler = pickle.load(f)
        print("✓ Loaded IF scaler")
        
        # Load LSTM scaler (1 feature)
        with open(self.lstm_scaler_path, 'rb') as f:
            self.lstm_scaler = pickle.load(f)
        print("✓ Loaded LSTM scaler")
        
        # Load metadata
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
                self.lstm_threshold = self.metadata.get('lstm_threshold', 0.01)
                self.sequence_length = self.metadata.get('sequence_length', 24)
        
        print(f"✓ Models loaded successfully")
        print(f"  LSTM threshold: {self.lstm_threshold:.6f}")
    
    def _load_last_detection_time(self):
        """Load last processed timestamp with lock protection"""
        lock = FileLock(str(self.detection_state_path) + ".lock")
        with lock:
            if self.detection_state_path.exists():
                try:
                    state = json.loads(self.detection_state_path.read_text())
                    ts = state.get("last_processed_timestamp")
                    return pd.to_datetime(ts) if ts else None
                except Exception:
                    return None
        return None

    def _save_last_detection_time(self, ts: pd.Timestamp):
        """Save last processed timestamp with lock protection"""
        lock = FileLock(str(self.detection_state_path) + ".lock")
        with lock:
            self.detection_state_path.write_text(json.dumps({
                "last_processed_timestamp": ts.isoformat()
            }, indent=2))

    def _load_last_alert_time(self):
        """Fallback: last alert timestamp from alerts.json"""
        lock = FileLock(str(self.alerts_path) + ".lock")
        with lock:
            if self.alerts_path.exists():
                try:
                    alerts_data = json.loads(self.alerts_path.read_text())
                    alerts = alerts_data.get("alerts", [])
                    if not alerts:
                        return None
                    latest = max(
                        (a.get("timestamp") for a in alerts if a.get("timestamp")),
                        default=None
                    )
                    return pd.to_datetime(latest) if latest else None
                except Exception:
                    return None
        return None

    def _load_existing_alert_timestamps(self):
        """Load existing alert timestamps to prevent duplicates"""
        lock = FileLock(str(self.alerts_path) + ".lock")
        with lock:
            if self.alerts_path.exists():
                try:
                    alerts_data = json.loads(self.alerts_path.read_text())
                    return {
                        a.get("timestamp")
                        for a in alerts_data.get("alerts", [])
                        if a.get("timestamp")
                    }
                except Exception:
                    return set()
        return set()
    
    def load_buffer_data(self):
        """Load buffer with lock protection"""
        buffer_file = self.data_dir / "buffer.csv"
        lock = FileLock(str(buffer_file) + ".lock")
        
        with lock:
            if not buffer_file.exists():
                raise FileNotFoundError("Buffer file not found")
            df = pd.read_csv(buffer_file)
        
        return df
    
    def detect_with_isolation_forest(self, df):
        """Stage 1: Isolation Forest detection"""
        features = ['power_kw', 'hour', 'day_of_week', 'is_weekend']
        X = df[features].copy()
        
        # Standardize using IF scaler (4 features)
        X_scaled = self.if_scaler.transform(X)
        
        # Predict
        predictions = self.if_model.predict(X_scaled)
        scores = self.if_model.score_samples(X_scaled)
        
        # Mark anomalies
        df['if_prediction'] = predictions
        df['if_score'] = scores
        df['if_anomaly'] = (predictions == -1).astype(int)
        
        if_count = df['if_anomaly'].sum()
        print(f"  IF detected: {if_count} candidate spikes")
        
        return df
    
    def create_sequences(self, data, seq_length):
        """Create sequences for LSTM"""
        sequences = []
        for i in range(len(data) - seq_length + 1):
            sequences.append(data[i:i + seq_length])
        return np.array(sequences)
    
    def detect_with_lstm(self, df):
        """Stage 2: LSTM verification"""
        # Prepare sequences using LSTM scaler (1 feature: power_kw only)
        power_data = df['power_kw'].values
        power_scaled = self.lstm_scaler.transform(power_data.reshape(-1, 1))
        
        if len(power_scaled) < self.sequence_length:
            print(f"  LSTM skipped: Need {self.sequence_length} hours, have {len(power_scaled)}")
            df['lstm_anomaly'] = 0
            df['lstm_error'] = 0.0
            return df
        
        X_lstm = self.create_sequences(power_scaled, self.sequence_length)
        
        # Predict
        X_pred = self.lstm_model.predict(X_lstm, verbose=0)
        reconstruction_errors = np.mean(np.abs(X_pred - X_lstm), axis=(1, 2))
        
        # Align with dataframe
        lstm_errors = np.concatenate([
            np.zeros(self.sequence_length - 1),
            reconstruction_errors
        ])
        
        lstm_anomalies = np.concatenate([
            np.zeros(self.sequence_length - 1, dtype=int),
            (reconstruction_errors > self.lstm_threshold).astype(int)
        ])
        
        df['lstm_error'] = lstm_errors
        df['lstm_anomaly'] = lstm_anomalies
        
        lstm_count = lstm_anomalies.sum()
        print(f"  LSTM verified: {lstm_count} pattern anomalies")
        
        return df
    
    def hybrid_decision(self, df):
        """Combine IF + LSTM for final decision"""
        # Both models must agree
        df['confirmed_spike'] = (
            (df['if_anomaly'] == 1) & (df['lstm_anomaly'] == 1)
        ).astype(int)
        
        confirmed = df['confirmed_spike'].sum()
        print(f"  ✓ Confirmed spikes: {confirmed}")
        
        return df
    
    def create_alert(self, row, baseline_kw):
        """Create alert object"""
        deviation = ((row['power_kw'] / baseline_kw - 1) * 100) if baseline_kw > 0 else 0
        
        return {
            "timestamp": row['timestamp'],
            "power_kw": float(row['power_kw']),
            "baseline_kw": float(baseline_kw),
            "deviation_percent": float(deviation),
            "alert_type": "consumption_spike",
            "if_score": float(row.get('if_score', 0)),
            "lstm_error": float(row.get('lstm_error', 0)),
            "severity": None,
            "status": None
        }
    
    def save_alerts(self, alerts):
        """Save alerts via FastAPI endpoint"""
        api_url = "http://localhost:8000/api/alerts"
        
        for alert in alerts:
            try:
                print(f"  📤 Sending alert to API: {alert['timestamp']}")
                response = requests.post(api_url, json=alert, timeout=5)
                print(f"     Response status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"  ✓ Alert saved via API: {alert['timestamp']}")
                    try:
                        saved_alert = response.json()
                        self._archive_alert_to_csv(saved_alert)
                    except Exception:
                        self._archive_alert_to_csv(alert)
                else:
                    print(f"  ✗ API error ({response.status_code}): {response.text}")
                    print(f"     Using fallback...")
                    self._save_alert_directly(alert)
            except Exception as e:
                print(f"  ✗ API unavailable ({type(e).__name__}: {e})")
                print(f"     Using fallback...")
                self._save_alert_directly(alert)
    
    def _save_alert_directly(self, alert):
        """Fallback: save directly to JSON if API is unavailable"""
        lock = FileLock(str(self.alerts_path) + ".lock")
        
        with lock:
            if self.alerts_path.exists():
                with open(self.alerts_path, 'r') as f:
                    alerts_data = json.load(f)
            else:
                alerts_data = {
                    "alerts": [],
                    "last_updated": None,
                    "total_count": 0
                }
            
            alert['id'] = alerts_data['total_count'] + 1
            alert['created_at'] = datetime.now().isoformat()
            alerts_data['alerts'].append(alert)
            alerts_data['total_count'] += 1
            alerts_data['last_updated'] = datetime.now().isoformat()
            
            if len(alerts_data['alerts']) > 1000:
                alerts_data['alerts'] = alerts_data['alerts'][-1000:]
            
            with open(self.alerts_path, 'w') as f:
                json.dump(alerts_data, f, indent=2)
        
        # ✅ Archive alert to CSV
        self._archive_alert_to_csv(alert)
        
        print(f"  ✓ Alert saved directly to file: {alert['timestamp']}")
    
    def _archive_alert_to_csv(self, alert):
        """Archive alert to alerts_archive.csv for long-term analysis"""
        alerts_archive = self.data_dir / "alerts_archive.csv"
        lock = FileLock(str(alerts_archive) + ".lock")
        
        alert_row = pd.DataFrame([{
            'alert_id': alert.get('id'),
            'timestamp': alert['timestamp'],
            'power_kw': alert['power_kw'],
            'baseline_kw': alert['baseline_kw'],
            'deviation_percent': alert['deviation_percent'],
            'severity': alert.get('severity', 'medium'),
            'status': alert.get('status', 'active'),
            'if_score': alert.get('if_score'),
            'lstm_error': alert.get('lstm_error'),
            'created_at': alert.get('created_at', datetime.now().isoformat())
        }])
        
        with lock:
            if alerts_archive.exists():
                archive_df = pd.read_csv(alerts_archive)
                archive_df = pd.concat([archive_df, alert_row], ignore_index=True)
            else:
                archive_df = alert_row
            archive_df.to_csv(alerts_archive, index=False)
    
    def run_detection(self):
        """Run complete anomaly detection pipeline"""
        print("\n" + "=" * 70)
        print("ANOMALY DETECTION - RUNNING")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Load data
        print("📊 Loading buffer data...")
        df = self.load_buffer_data()
        print(f"  ✓ Loaded {len(df)} readings")
        
        # Stage 1: Isolation Forest
        print("\n🔍 Stage 1: Isolation Forest Detection")
        df = self.detect_with_isolation_forest(df)
        
        # Stage 2: LSTM
        print("\n🧠 Stage 2: LSTM Pattern Verification")
        df = self.detect_with_lstm(df)
        
        # Hybrid decision
        print("\n✅ Stage 3: Hybrid Decision")
        df = self.hybrid_decision(df)
        
        # Extract confirmed spikes
        confirmed_spikes = df[df['confirmed_spike'] == 1]
        
        # ✅ Use detection_state; fallback to most recent alert timestamp
        last_ts = self._load_last_detection_time() or self._load_last_alert_time()
        existing_ts = self._load_existing_alert_timestamps()
        
        # Only emit alerts for new rows
        if last_ts is not None:
            confirmed_spikes = confirmed_spikes[
                pd.to_datetime(confirmed_spikes['timestamp']) > last_ts
            ]
        
        if len(confirmed_spikes) > 0:
            print(f"\n🚨 ALERTS GENERATED: {len(confirmed_spikes)}")
            
            # Load baseline with weekday/weekend separation
            baseline_file = self.data_dir / "baseline.json"
            baseline_json = {}
            if baseline_file.exists():
                with open(baseline_file, 'r') as f:
                    baseline_json = json.load(f)
            
            weekday_baseline = baseline_json.get('weekday_baseline', {})
            weekend_baseline = baseline_json.get('weekend_baseline', {})
            hourly_baseline = baseline_json.get('hourly_baseline', {})
            
            # Create alerts
            alerts = []
            for idx, row in confirmed_spikes.iterrows():
                if row['timestamp'] in existing_ts:
                    continue

                hour_str = str(int(row.get('hour', 0)))
                
                # Determine if this is a weekday or weekend reading
                timestamp = pd.to_datetime(row['timestamp'])
                day_of_week = timestamp.dayofweek  # 0=Monday, 6=Sunday
                is_weekend = day_of_week >= 5
                
                # Select appropriate baseline
                if is_weekend and weekend_baseline:
                    baseline_data = weekend_baseline.get(hour_str, {})
                    baseline_type = "weekend"
                elif weekday_baseline:
                    baseline_data = weekday_baseline.get(hour_str, {})
                    baseline_type = "weekday"
                else:
                    # Fallback to hourly baseline
                    baseline_data = hourly_baseline.get(hour_str, {})
                    baseline_type = "hourly"
                
                baseline_kw = baseline_data.get('mean', row['power_kw'] * 0.5)
                
                alert = self.create_alert(row, baseline_kw)
                alert['baseline_type'] = baseline_type  # Track which baseline was used
                alerts.append(alert)
                
                print(f"  ⚡ {row['timestamp']}: {row['power_kw']:.3f} kW "
                      f"(+{alert['deviation_percent']:.1f}% above {baseline_type} baseline)")
            
            # Save alerts
            self.save_alerts(alerts)

            # ✅ Update last processed timestamp to newest row
            newest_ts = pd.to_datetime(df['timestamp']).max()
            self._save_last_detection_time(newest_ts)
            
        else:
            print("\n✅ No spikes detected - system operating normally")
        
        print("\n" + "=" * 70)
        print("DETECTION COMPLETE")
        print("=" * 70)
        
        return {
            "total_readings": len(df),
            "if_candidates": int(df['if_anomaly'].sum()),
            "lstm_detections": int(df['lstm_anomaly'].sum()),
            "confirmed_spikes": len(confirmed_spikes),
            "alerts": len(confirmed_spikes),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Test anomaly detector"""
    try:
        detector = AnomalyDetector()
        result = detector.run_detection()
        
        print("\n📊 Detection Summary:")
        print(f"  Total readings: {result['total_readings']}")
        print(f"  IF candidates: {result['if_candidates']}")
        print(f"  LSTM verifications: {result['lstm_detections']}")
        print(f"  Confirmed spikes: {result['confirmed_spikes']}")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Solution: Run model_trainer.py first to train models")
    except Exception as e:
        print(f"\n❌ Detection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()