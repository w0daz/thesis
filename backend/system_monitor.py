"""
IoT Energy Monitoring System - System Monitor
Check system health and display status
"""

from pathlib import Path
import json
from datetime import datetime, timedelta
from filelock import FileLock

class SystemMonitor:
    """Monitor system health and status"""
    
    def __init__(self, data_dir="../data", model_dir="../models"):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
    
    def check_buffer_status(self):
        """Check buffer file status"""
        buffer_file = self.data_dir / "buffer.csv"
        
        if not buffer_file.exists():
            return {
                "status": "missing",
                "message": "Buffer file not found",
                "recommendation": "Start sensor simulator"
            }
        
        import pandas as pd
        df = pd.read_csv(buffer_file)
        
        if len(df) == 0:
            return {
                "status": "empty",
                "message": "Buffer is empty",
                "recommendation": "Wait for sensor data"
            }
        
        # Check data age
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        latest_reading = df['timestamp'].max()
        age = datetime.now() - latest_reading
        
        if age > timedelta(minutes=5):
            status = "stale"
            message = f"Data is {age.seconds // 60} minutes old"
            recommendation = "Check if sensor simulator is running"
        else:
            status = "healthy"
            message = f"{len(df)} readings, updated {age.seconds} seconds ago"
            recommendation = None
        
        return {
            "status": status,
            "readings": len(df),
            "latest": latest_reading.strftime("%Y-%m-%d %H:%M:%S"),
            "age_seconds": age.seconds,
            "message": message,
            "recommendation": recommendation
        }
    
    def check_models_status(self):
        """Check if models are trained and available"""
        required_files = [
            "isolation_forest.pkl",
            "lstm_autoencoder.h5",
            "if_scaler.pkl",
            "scaler.pkl",
            "model_metadata.json"
        ]
        
        missing = []
        for file in required_files:
            if not (self.model_dir / file).exists():
                missing.append(file)
        
        if missing:
            return {
                "status": "missing",
                "message": f"Missing {len(missing)} model files",
                "missing_files": missing,
                "recommendation": "Run: python backend/model_trainer.py"
            }
        
        # Check model metadata
        metadata_file = self.model_dir / "model_metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        trained_at = datetime.fromisoformat(metadata['trained_at'])
        age = datetime.now() - trained_at
        
        if age > timedelta(days=7):
            status = "outdated"
            message = f"Models trained {age.days} days ago"
            recommendation = "Consider retraining with fresh data"
        else:
            status = "healthy"
            message = f"Models trained {age.days} days ago"
            recommendation = None
        
        return {
            "status": status,
            "trained_at": trained_at.strftime("%Y-%m-%d %H:%M:%S"),
            "age_days": age.days,
            "sequence_length": metadata.get('sequence_length'),
            "message": message,
            "recommendation": recommendation
        }
    
    def check_alerts_status(self):
        """Check alerts file status"""
        alerts_file = self.data_dir / "alerts.json"
        
        if not alerts_file.exists():
            return {
                "status": "missing",
                "total_alerts": 0,
                "message": "No alerts file found",
                "recommendation": "File will be created automatically"
            }
        
        lock = FileLock(str(alerts_file) + ".lock")
        with lock:
            with open(alerts_file, 'r') as f:
                alerts_data = json.load(f)
        
        alerts_list = alerts_data.get('alerts', [])
        total = len(alerts_list)
        last_updated = alerts_data.get('last_updated')
        
        return {
            "status": "healthy",
            "total_alerts": total,
            "last_updated": last_updated,
            "message": f"{total} total alerts",
            "recommendation": None
        }
    
    def get_system_health(self):
        """Get overall system health"""
        buffer = self.check_buffer_status()
        models = self.check_models_status()
        alerts = self.check_alerts_status()
        
        # Determine overall status
        statuses = [buffer['status'], models['status'], alerts['status']]
        
        if 'missing' in statuses:
            overall = "degraded"
        elif 'stale' in statuses or 'outdated' in statuses:
            overall = "warning"
        else:
            overall = "healthy"
        
        return {
            "overall_status": overall,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "buffer": buffer,
                "models": models,
                "alerts": alerts
            }
        }
    
    def print_status(self):
        """Print formatted system status"""
        health = self.get_system_health()
        
        print("\n" + "=" * 70)
        print("🏥 SYSTEM HEALTH CHECK")
        print("=" * 70)
        print(f"Time: {health['timestamp']}")
        print(f"Overall Status: {health['overall_status'].upper()}")
        
        print("\n📊 BUFFER STATUS:")
        buffer = health['components']['buffer']
        print(f"  Status: {buffer['status']}")
        print(f"  {buffer['message']}")
        if buffer.get('recommendation'):
            print(f"  💡 {buffer['recommendation']}")
        
        print("\n🤖 MODELS STATUS:")
        models = health['components']['models']
        print(f"  Status: {models['status']}")
        print(f"  {models['message']}")
        if models.get('recommendation'):
            print(f"  💡 {models['recommendation']}")
        
        print("\n🚨 ALERTS STATUS:")
        alerts = health['components']['alerts']
        print(f"  Status: {alerts['status']}")
        print(f"  {alerts['message']}")
        
        print("\n" + "=" * 70)


def main():
    """Run system monitor"""
    monitor = SystemMonitor()
    monitor.print_status()


if __name__ == "__main__":
    main()