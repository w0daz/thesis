"""
IoT Energy Monitoring System - Sensor Simulator
Simulates ACS712/SCT-013 current sensor readings for household power consumption
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import time
from filelock import FileLock

class PowerSensorSimulator:
    """
    Simulates realistic household electricity consumption patterns
    Based on typical residential usage profiles
    """
    
    def __init__(self, data_dir="data"):
        """
        Initialize the sensor simulator
        
        Args:
            data_dir: Directory to store buffer.csv
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.buffer_file = self.data_dir / "buffer.csv"
        
        # Sensor configuration
        self.voltage = 230  # Volts (EU standard)
        self.sample_rate = 60  # Seconds between readings
        self.buffer_hours = 24  # Keep 24 hours of data
        
        print("🔌 Power Sensor Simulator Initialized")
        print(f"   Buffer file: {self.buffer_file}")
        print(f"   Sample rate: {self.sample_rate}s")
        print(f"   Buffer size: {self.buffer_hours}h")
        
    def get_base_consumption(self, hour):
        """
        Get base power consumption for a given hour
        Follows typical household daily patterns
        
        Args:
            hour: Hour of day (0-23)
            
        Returns:
            Base power consumption in kW
        """
        # Realistic hourly consumption patterns
        patterns = {
            # Night (00:00 - 06:00): Low consumption (refrigerator, standby devices)
            range(0, 6): lambda: np.random.uniform(0.3, 0.8),
            
            # Morning (06:00 - 09:00): High consumption (breakfast, showers)
            range(6, 9): lambda: np.random.uniform(1.5, 3.5),
            
            # Day (09:00 - 17:00): Moderate consumption (away at work/school)
            range(9, 17): lambda: np.random.uniform(0.8, 1.5),
            
            # Evening (17:00 - 23:00): High consumption (cooking, entertainment)
            range(17, 23): lambda: np.random.uniform(2.0, 4.5),
            
            # Late night (23:00 - 00:00): Moderate to low
            range(23, 24): lambda: np.random.uniform(0.8, 1.5),
        }
        
        # Find matching pattern
        for hour_range, consumption_func in patterns.items():
            if hour in hour_range:
                return consumption_func()
        
        # Fallback (shouldn't happen)
        return np.random.uniform(0.5, 2.0)
    
    def add_weekday_pattern(self, power, day_of_week):
        """
        Adjust consumption based on weekday vs weekend
        
        Args:
            power: Base power consumption
            day_of_week: 0=Monday, 6=Sunday
            
        Returns:
            Adjusted power consumption
        """
        # Weekends: More home usage during the day
        if day_of_week >= 5:  # Saturday or Sunday
            power *= np.random.uniform(1.05, 1.15)
        
        return power
    
    def add_seasonal_variation(self, power, month):
        """
        Add seasonal variations (heating/cooling)
        
        Args:
            power: Base power consumption
            month: Month (1-12)
            
        Returns:
            Adjusted power consumption
        """
        # Winter months (Dec, Jan, Feb): Higher consumption (heating)
        if month in [12, 1, 2]:
            power *= np.random.uniform(1.2, 1.4)
        
        # Summer months (Jun, Jul, Aug): Moderate increase (cooling)
        elif month in [6, 7, 8]:
            power *= np.random.uniform(1.05, 1.15)
        
        return power
    
    def add_random_noise(self, power):
        """
        Add small random fluctuations (normal sensor noise)
        
        Args:
            power: Base power consumption
            
        Returns:
            Power with noise added
        """
        noise = np.random.normal(0, 0.05)  # Small Gaussian noise
        return max(0.1, power + noise)  # Ensure non-negative
    
    def inject_spike(self):
        """
        Simulate consumption spike (large appliance turning on)
        
        Returns:
            Spike magnitude in kW (or 0 if no spike)
        """
        # 3% probability of spike occurring
        if np.random.random() < 0.03:
            # Different spike types
            spike_types = [
                ("Water heater", np.random.uniform(2.0, 3.5)),
                ("Electric oven", np.random.uniform(2.5, 4.0)),
                ("Air conditioner", np.random.uniform(1.5, 2.5)),
                ("Washing machine", np.random.uniform(1.0, 2.0)),
                ("Multiple appliances", np.random.uniform(3.0, 5.0)),
            ]
            
            spike_type, magnitude = spike_types[np.random.randint(0, len(spike_types))]
            print(f"   ⚡ SPIKE: {spike_type} (+{magnitude:.2f} kW)")
            return magnitude
        
        return 0.0
    
    def read_sensor(self):
        """
        Simulate a single sensor reading
        
        Returns:
            dict with timestamp and power reading
        """
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        month = now.month
        
        # Get base consumption for this hour
        power = self.get_base_consumption(hour)
        
        # Apply patterns
        power = self.add_weekday_pattern(power, day_of_week)
        power = self.add_seasonal_variation(power, month)
        power = self.add_random_noise(power)
        
        # Add potential spike
        spike = self.inject_spike()
        power += spike
        
        # Ensure realistic range (0.1 - 10.0 kW for residential)
        power = np.clip(power, 0.1, 10.0)
        
        return {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "power_kw": round(power, 3),
            "voltage": self.voltage,
            "current_a": round(power * 1000 / self.voltage, 2),  # I = P/V
            "hour": hour,
            "day_of_week": day_of_week,
            "is_weekend": int(day_of_week >= 5),
            "is_spike": int(spike > 0)
        }
    
    def save_to_buffer(self, reading):
        """
        Save reading to CSV buffer (rolling 24-hour window)
        
        Args:
            reading: Dictionary with sensor reading data
        """
        buffer_lock = FileLock(str(self.buffer_file) + ".lock")
        
        # Save to rolling buffer with lock
        with buffer_lock:
            if self.buffer_file.exists():
                df = pd.read_csv(self.buffer_file)
            else:
                df = pd.DataFrame()
            
            new_row = pd.DataFrame([reading])
            df = pd.concat([df, new_row], ignore_index=True)
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            cutoff_time = datetime.now() - timedelta(hours=self.buffer_hours)
            df = df[df['timestamp'] >= cutoff_time]
            
            df.to_csv(self.buffer_file, index=False)
            buffer_size = len(df)
        
        # ✅ Append every reading to full-history archive (with lock)
        archive_file = self.data_dir / "sensor_archive.csv"
        archive_lock = FileLock(str(archive_file) + ".lock")

        archive_row = pd.DataFrame([reading])
        with archive_lock:
            if archive_file.exists():
                archive_df = pd.read_csv(archive_file)
                archive_df = pd.concat([archive_df, archive_row], ignore_index=True)
            else:
                archive_df = archive_row
            archive_df.to_csv(archive_file, index=False)
        
        return buffer_size
    
    def start_continuous_reading(self, duration_minutes=None):
        """
        Start continuous sensor readings (simulates real sensor)
        
        Args:
            duration_minutes: How long to run (None = run forever)
        """
        print(f"\n{'='*70}")
        print("🚀 STARTING CONTINUOUS SENSOR READINGS")
        print(f"{'='*70}")
        print(f"Sample rate: Every {self.sample_rate} seconds")
        print(f"Buffer window: {self.buffer_hours} hours")
        
        if duration_minutes:
            print(f"Duration: {duration_minutes} minutes")
        else:
            print("Duration: Continuous (Press Ctrl+C to stop)")
        
        print(f"\n⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        start_time = datetime.now()
        reading_count = 0
        
        try:
            while True:
                # Take reading
                reading = self.read_sensor()
                buffer_size = self.save_to_buffer(reading)
                reading_count += 1
                
                # Display reading
                print(f"[{reading['timestamp']}] "
                      f"Power: {reading['power_kw']:.3f} kW | "
                      f"Current: {reading['current_a']:.2f} A | "
                      f"Buffer: {buffer_size} readings")
                
                # Check if duration limit reached
                if duration_minutes:
                    elapsed = (datetime.now() - start_time).total_seconds() / 60
                    if elapsed >= duration_minutes:
                        print(f"\n✅ Duration limit reached ({duration_minutes} min)")
                        break
                
                # Wait for next sample
                time.sleep(self.sample_rate)
                
        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print("⏹️  SENSOR READINGS STOPPED")
            print(f"{'='*70}")
            print(f"Total readings: {reading_count}")
            print(f"Duration: {(datetime.now() - start_time).total_seconds() / 60:.1f} minutes")
            print(f"Buffer file: {self.buffer_file}")
            print(f"{'='*70}\n")


def main():
    """Main function for testing sensor simulator"""
    print("=" * 70)
    print("IOT ENERGY MONITORING - SENSOR SIMULATOR")
    print("Sprint 2: Realistic Power Consumption Generation")
    print("=" * 70)
    
    # Create simulator
    sensor = PowerSensorSimulator(data_dir="../data")
    
    # Menu
    print("\nOptions:")
    print("1. Generate single reading (test)")
    print("2. Generate 5 readings (quick test)")
    print("3. Generate 1 hour of data (60 readings)")
    print("4. Start continuous readings (run until stopped)")
    print("5. Generate 24 hours of data (1440 readings)")
    print("6. Generate 48 hours of data (2880 readings)")
    
    choice = input("\nSelect option (1-6): ")
    
    if choice == "1":
        reading = sensor.read_sensor()
        sensor.save_to_buffer(reading)
        print(f"\n✅ Single reading generated:")
        print(f"   {reading}")
        
    elif choice == "2":
        print("\n🔄 Generating 5 readings...")
        for i in range(5):
            reading = sensor.read_sensor()
            sensor.save_to_buffer(reading)
            print(f"   {i+1}. {reading['timestamp']} - {reading['power_kw']:.3f} kW")
            time.sleep(1)
        print("✅ Complete!")
        
    elif choice == "3":
        sensor.start_continuous_reading(duration_minutes=60)
        
    elif choice == "4":
        sensor.start_continuous_reading()
        
    elif choice == "5":
        sensor.start_continuous_reading(duration_minutes=1440)
        
    elif choice == "6":
        sensor.start_continuous_reading(duration_minutes=2880)
        
    else:
        print("❌ Invalid option")


if __name__ == "__main__":
    main()