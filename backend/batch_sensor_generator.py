import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from filelock import FileLock


def iso_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class BatchPowerSensorGenerator:
    """Generate a full block of synthetic power readings with timestamps."""

    def __init__(self, data_dir: Path | str | None = None, voltage: int = 230, sample_rate: int = 60, buffer_hours: int = 24):
        if data_dir is None:
            self.data_dir = Path(__file__).resolve().parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.voltage = voltage
        self.sample_rate = sample_rate
        self.buffer_hours = buffer_hours
        self.buffer_file = self.data_dir / "buffer.csv"
        self.archive_file = self.data_dir / "sensor_archive.csv"

    def get_base_consumption(self, hour: int) -> float:
        patterns = {
            range(0, 6): lambda: np.random.uniform(0.3, 0.8),
            range(6, 9): lambda: np.random.uniform(1.5, 3.5),
            range(9, 17): lambda: np.random.uniform(0.8, 1.5),
            range(17, 23): lambda: np.random.uniform(2.0, 4.5),
            range(23, 24): lambda: np.random.uniform(0.8, 1.5),
        }
        for hour_range, func in patterns.items():
            if hour in hour_range:
                return func()
        return np.random.uniform(0.5, 2.0)

    def add_weekday_pattern(self, power: float, day_of_week: int) -> float:
        if day_of_week >= 5:
            power *= np.random.uniform(1.05, 1.15)
        return power

    def add_seasonal_variation(self, power: float, month: int) -> float:
        if month in [12, 1, 2]:
            power *= np.random.uniform(1.2, 1.4)
        elif month in [6, 7, 8]:
            power *= np.random.uniform(1.05, 1.15)
        return power

    def add_random_noise(self, power: float) -> float:
        noise = np.random.normal(0, 0.05)
        return max(0.1, power + noise)

    def inject_spike(self) -> float:
        if np.random.random() < 0.03:
            spike_types = [
                ("Water heater", np.random.uniform(2.0, 3.5)),
                ("Electric oven", np.random.uniform(2.5, 4.0)),
                ("Air conditioner", np.random.uniform(1.5, 2.5)),
                ("Washing machine", np.random.uniform(1.0, 2.0)),
                ("Multiple appliances", np.random.uniform(3.0, 5.0)),
            ]
            _, magnitude = spike_types[np.random.randint(0, len(spike_types))]
            return magnitude
        return 0.0

    def generate_reading(self, timestamp: datetime) -> dict:
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        month = timestamp.month
        power = self.get_base_consumption(hour)
        power = self.add_weekday_pattern(power, day_of_week)
        power = self.add_seasonal_variation(power, month)
        power = self.add_random_noise(power)
        spike = self.inject_spike()
        power += spike
        power = np.clip(power, 0.1, 10.0)
        return {
            "timestamp": iso_timestamp(timestamp),
            "power_kw": round(power, 3),
            "voltage": self.voltage,
            "current_a": round(power * 1000 / self.voltage, 2),
            "hour": hour,
            "day_of_week": day_of_week,
            "is_weekend": int(day_of_week >= 5),
            "is_spike": int(spike > 0),
        }

    def append_to_archive(self, readings: list[dict]):
        archive_lock = FileLock(str(self.archive_file) + ".lock")
        with archive_lock:
            if self.archive_file.exists():
                archive_df = pd.read_csv(self.archive_file)
                archive_df = pd.concat([archive_df, pd.DataFrame(readings)], ignore_index=True)
            else:
                archive_df = pd.DataFrame(readings)
            archive_df.to_csv(self.archive_file, index=False)

    def write_buffer(self, readings: list[dict]):
        last_rows = readings[-int(self.buffer_hours * 3600 / self.sample_rate):]
        buffer_lock = FileLock(str(self.buffer_file) + ".lock")
        with buffer_lock:
            df = pd.DataFrame(last_rows)
            df.to_csv(self.buffer_file, index=False)

    def generate(self, hours: float = 48.0, end_time: datetime | None = None, keep_existing_buffer: bool = False):
        if end_time is None:
            end_time = datetime.now()
        total_samples = int(hours * 3600 / self.sample_rate)
        start_time = end_time - timedelta(seconds=self.sample_rate * (total_samples - 1))
        timestamps = [start_time + timedelta(seconds=i * self.sample_rate) for i in range(total_samples)]
        readings = [self.generate_reading(ts) for ts in timestamps]

        print(f"Generating {len(readings)} readings from {iso_timestamp(start_time)} to {iso_timestamp(end_time)}")
        print(f"Data directory: {self.data_dir}")
        print(f"Archive file: {self.archive_file}")
        print(f"Buffer file: {self.buffer_file}")
        self.append_to_archive(readings)

        if not keep_existing_buffer:
            self.write_buffer(readings)
            print(f"Updated buffer.csv with the last {self.buffer_hours} hours of generated data.")
        else:
            print("Kept existing buffer.csv unchanged.")

        print(f"Appended {len(readings)} rows to sensor_archive.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate batch sensor readings for 24/48h experiments")
    parser.add_argument("--hours", type=float, default=48.0, help="Number of hours to generate")
    parser.add_argument("--end-time", type=str, default=None,
                        help="End timestamp for generated data in format YYYY-MM-DD HH:MM:SS (default = now)")
    parser.add_argument("--data-dir", type=str, default=None, help="Directory to store data files (default = repo data folder)")
    parser.add_argument("--keep-buffer", action="store_true",
                        help="Do not overwrite buffer.csv; only append to sensor_archive.csv")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.end_time:
        try:
            end_time = datetime.strptime(args.end_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise SystemExit("Invalid --end-time format. Use 'YYYY-MM-DD HH:MM:SS'.")
    else:
        end_time = None

    generator = BatchPowerSensorGenerator(data_dir=args.data_dir)
    generator.generate(hours=args.hours, end_time=end_time, keep_existing_buffer=args.keep_buffer)


if __name__ == "__main__":
    main()
