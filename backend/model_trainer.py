"""
IoT Energy Monitoring System - Model Trainer (FIXED)
Trains and saves Isolation Forest + LSTM Autoencoder models
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, RepeatVector, TimeDistributed
from tensorflow.keras.callbacks import EarlyStopping
import pickle
import json
from filelock import FileLock

class ModelTrainer:
    """Train and save anomaly detection models"""
    
    def __init__(self, data_dir="../data", model_dir="../models"):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        # Model paths
        self.if_model_path = self.model_dir / "isolation_forest.pkl"
        self.lstm_model_path = self.model_dir / "lstm_autoencoder.h5"
        self.if_scaler_path = self.model_dir / "if_scaler.pkl"
        self.lstm_scaler_path = self.model_dir / "scaler.pkl"
        self.metadata_path = self.model_dir / "model_metadata.json"
        
        # Hyperparameters
        self.sequence_length = 24
        self.contamination = 0.03
        
    def load_training_data(self, file_path=None):
        """
        Load data from buffer or archive for training
        
        Args:
            file_path: Optional path to specific file (e.g., sensor_archive.csv)
        """
        if file_path:
            # Load from specified file with lock
            lock = FileLock(str(file_path) + ".lock")
            with lock:
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                df = pd.read_csv(file_path)
            print(f"✓ Loaded {len(df)} records from {file_path.name}")
        else:
            # Default: load from buffer
            buffer_file = self.data_dir / "buffer.csv"
            lock = FileLock(str(buffer_file) + ".lock")
            
            with lock:
                if not buffer_file.exists():
                    raise FileNotFoundError(
                        "Buffer file not found. Run sensor simulator first to generate data."
                    )
                df = pd.read_csv(buffer_file)
            
            print(f"✓ Loaded {len(df)} records from buffer")
        
        return df
    
    def prepare_features(self, df):
        """Prepare features for Isolation Forest"""
        features = ['power_kw', 'hour', 'day_of_week', 'is_weekend']
        
        missing = [f for f in features if f not in df.columns]
        if missing:
            raise ValueError(f"Missing features: {missing}")
        
        X = df[features].copy()
        
        if_scaler = StandardScaler()
        X_scaled = if_scaler.fit_transform(X)
        
        print(f"✓ Prepared features for IF: {features}")
        return X_scaled, if_scaler
    
    def train_isolation_forest(self, X_scaled):
        """Train Isolation Forest model"""
        print("\n🤖 Training Isolation Forest...")
        print(f"   Samples: {len(X_scaled)}")
        print(f"   Contamination: {self.contamination * 100}%")
        
        if len(X_scaled) < 10:
            raise ValueError(
                f"Insufficient data for Isolation Forest training.\n"
                f"   Required: At least 10 records\n"
                f"   Available: {len(X_scaled)} records\n"
                f"   Solution: Run sensor simulator for at least 10 hours"
            )
        
        model = IsolationForest(
            n_estimators=200,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )
        
        model.fit(X_scaled)
        
        predictions = model.predict(X_scaled)
        anomalies = (predictions == -1).sum()
        
        print(f"✓ Training complete")
        print(f"  Detected anomalies in training: {anomalies} ({anomalies/len(X_scaled)*100:.1f}%)")
        
        return model
    
    def create_sequences(self, data, seq_length):
        """Create sequences for LSTM"""
        sequences = []
        for i in range(len(data) - seq_length + 1):
            sequences.append(data[i:i + seq_length])
        return np.array(sequences)
    
    def train_lstm_autoencoder(self, df):
        """Train LSTM Autoencoder"""
        print("\n🧠 Training LSTM Autoencoder...")
        
        data_length = len(df)
        MIN_SEQUENCES = 20
        
        # Dynamically adjust sequence length
        if data_length < self.sequence_length + MIN_SEQUENCES:
            old_seq = self.sequence_length
            self.sequence_length = max(3, data_length // 3)
            print(f"   ⚠ Adjusted sequence length: {old_seq} → {self.sequence_length}")
        
        if data_length < self.sequence_length + MIN_SEQUENCES:
            raise ValueError(
                f"Insufficient data for LSTM training.\n"
                f"   Required: At least {self.sequence_length + MIN_SEQUENCES} records\n"
                f"   Available: {data_length} records\n"
                f"   Solution: Run sensor simulator for longer duration"
            )
        
        print(f"   Samples: {data_length}")
        print(f"   Sequence length: {self.sequence_length}")
        
        # Prepare data
        power_data = df['power_kw'].values.reshape(-1, 1)
        lstm_scaler = StandardScaler()
        power_scaled = lstm_scaler.fit_transform(power_data)
        
        sequences = self.create_sequences(power_scaled, self.sequence_length)
        print(f"   Created {len(sequences)} sequences")
        
        if len(sequences) < MIN_SEQUENCES:
            raise ValueError(f"Need at least {MIN_SEQUENCES} sequences, got {len(sequences)}")
        
        # Build model
        model = Sequential([
            LSTM(32, activation='relu', return_sequences=True, input_shape=(self.sequence_length, 1)),
            Dropout(0.2),
            LSTM(16, activation='relu', return_sequences=False),
            Dropout(0.2),
            RepeatVector(self.sequence_length),
            LSTM(16, activation='relu', return_sequences=True),
            Dropout(0.2),
            LSTM(32, activation='relu', return_sequences=True),
            TimeDistributed(Dense(1))
        ])
        
        model.compile(optimizer='adam', loss='mse')
        
        print("\n   Training LSTM...")
        history = model.fit(
            sequences, sequences,
            epochs=50,
            batch_size=16,
            validation_split=0.2,
            callbacks=[EarlyStopping(patience=5, restore_best_weights=True)],
            verbose=0
        )
        
        print(f"✓ Training complete (epochs: {len(history.history['loss'])})")
        
        # Calculate threshold
        predictions = model.predict(sequences, verbose=0)
        reconstruction_errors = np.mean(np.abs(sequences - predictions), axis=(1, 2))
        
        if len(reconstruction_errors) < 50:
            threshold_percentile = 90
        else:
            threshold_percentile = 95
        
        threshold = np.percentile(reconstruction_errors, threshold_percentile)
        
        print(f"  Alert threshold ({threshold_percentile}th percentile): {threshold:.6f}")
        
        return model, lstm_scaler, threshold
    
    def save_models(self, if_model, lstm_model, if_scaler, lstm_scaler, threshold):
        """Save all models and metadata with lock protection"""
        print("\n💾 Saving models...")
        
        # Use single lock for all model files
        lock_file = self.model_dir / ".models.lock"
        lock = FileLock(str(lock_file))
        
        with lock:
            # Save Isolation Forest
            with open(self.if_model_path, 'wb') as f:
                pickle.dump(if_model, f)
            print(f"✓ Saved: {self.if_model_path}")
            
            # Save LSTM
            lstm_model.save(self.lstm_model_path)
            print(f"✓ Saved: {self.lstm_model_path}")
            
            # Save IF scaler
            with open(self.if_scaler_path, 'wb') as f:
                pickle.dump(if_scaler, f)
            print(f"✓ Saved: {self.if_scaler_path}")
            
            # Save LSTM scaler
            with open(self.lstm_scaler_path, 'wb') as f:
                pickle.dump(lstm_scaler, f)
            print(f"✓ Saved: {self.lstm_scaler_path}")
            
            # Save metadata
            metadata = {
                "trained_at": datetime.now().isoformat(),
                "sequence_length": self.sequence_length,
                "contamination": self.contamination,
                "lstm_threshold": float(threshold),
                "model_versions": {
                    "isolation_forest": "sklearn",
                    "lstm": "tensorflow"
                }
            }
            
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"✓ Saved: {self.metadata_path}")
    
    def train_all(self, data_source=None):
        """
        Train all models
        
        Args:
            data_source: Optional Path to data file (defaults to buffer.csv)
        """
        print("=" * 70)
        print("MODEL TRAINING - ANOMALY DETECTION")
        print("=" * 70)
        
        # Load data
        df = self.load_training_data(data_source)
        
        # Show data statistics
        print(f"\n📊 Data Statistics:")
        print(f"   Records: {len(df)}")
        print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"   Power range: {df['power_kw'].min():.3f} - {df['power_kw'].max():.3f} kW")
        
        # Check minimum requirements
        if len(df) < 50:
            print("\n⚠️ WARNING: Limited data available")
            print("   Model performance may be suboptimal")
            print("   Recommendation: Collect at least 48 hours of data")
        
        # Train Isolation Forest
        X_scaled, if_scaler = self.prepare_features(df)
        if_model = self.train_isolation_forest(X_scaled)
        
        # Train LSTM
        lstm_model, lstm_scaler, threshold = self.train_lstm_autoencoder(df)
        
        # Save models
        self.save_models(if_model, lstm_model, if_scaler, lstm_scaler, threshold)
        
        print("\n" + "=" * 70)
        print("✅ TRAINING COMPLETE")
        print("=" * 70)
        print(f"Models saved to: {self.model_dir}")
        print("\nNext steps:")
        print("  1. Start the web server: python backend/main.py")
        print("  2. Visit: http://localhost:8000")
        print("  3. Monitor real-time anomaly detection")
    
    def train_from_archive(self, archive_file):
        """
        ✅ NEW: Train directly from sensor_archive.csv with lock protection
        This avoids dangerous buffer swapping during retraining
        
        Args:
            archive_file: Path to sensor_archive.csv
        """
        print("=" * 70)
        print("MODEL RETRAINING - FROM ARCHIVE")
        print("=" * 70)
        
        archive_path = Path(archive_file)
        
        # Load archive data with lock
        lock = FileLock(str(archive_path) + ".lock")
        with lock:
            if not archive_path.exists():
                raise FileNotFoundError(f"Archive not found: {archive_path}")
            df = pd.read_csv(archive_path)
        
        print(f"✓ Loaded {len(df)} records from archive")
        
        # Show data statistics
        print(f"\n📊 Archive Statistics:")
        print(f"   Records: {len(df)}")
        if 'timestamp' in df.columns:
            print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"   Power range: {df['power_kw'].min():.3f} - {df['power_kw'].max():.3f} kW")
        
        # Train models
        X_scaled, if_scaler = self.prepare_features(df)
        if_model = self.train_isolation_forest(X_scaled)
        lstm_model, lstm_scaler, threshold = self.train_lstm_autoencoder(df)
        
        # Save models
        self.save_models(if_model, lstm_model, if_scaler, lstm_scaler, threshold)
        
        print("\n" + "=" * 70)
        print("✅ RETRAINING COMPLETE")
        print("=" * 70)


def main():
    """Run model training"""
    trainer = ModelTrainer()
    trainer.train_all()


if __name__ == "__main__":
    main()