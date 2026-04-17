"""
IoT Energy Monitoring System - Background Sensor Runner
Runs sensor simulator continuously in the background
"""

from sensor_simulator import PowerSensorSimulator
import time
import sys
from datetime import datetime

def run_background_sensor(duration_hours=None):
    """
    Run sensor simulator in background mode
    
    Args:
        duration_hours: How many hours to run (None = forever)
    """
    print("=" * 70)
    print("🔌 BACKGROUND SENSOR - STARTING")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if duration_hours:
        print(f"Duration: {duration_hours} hours")
    else:
        print("Duration: Continuous (until stopped)")
    
    print("\nThis will run in the background.")
    print("Press Ctrl+C to stop gracefully.")
    print("=" * 70 + "\n")
    
    # Create simulator
    sensor = PowerSensorSimulator(data_dir="../data")
    
    # Calculate duration in minutes
    duration_minutes = duration_hours * 60 if duration_hours else None
    
    try:
        # Run continuously
        sensor.start_continuous_reading(duration_minutes=duration_minutes)
        
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("🛑 Background sensor stopped by user")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Sensor error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
            run_background_sensor(duration_hours=hours)
        except ValueError:
            print("❌ Invalid duration. Usage: python sensor_background.py [hours]")
            print("   Example: python sensor_background.py 24")
    else:
        # Run forever
        run_background_sensor()