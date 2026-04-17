"""
IoT Energy Monitoring System - Automated Retraining Pipeline
Uses archived historical data for more robust model training
Completes the ML feedback loop: Collect → Transfer → Store → Analyze → Decide → Learn
"""

import json
from pathlib import Path
from datetime import datetime
from model_trainer import ModelTrainer
from filelock import FileLock
import pandas as pd

class RetrainingPipeline:
    """Minimal feedback loop for continuous learning"""
    
    def __init__(self, data_dir="../data", model_dir="../models"):
        self.data_dir = Path(data_dir)
        self.feedback_file = self.data_dir / "feedback.json"
        self.archive_file = self.data_dir / "sensor_archive.csv"
        self.trainer = ModelTrainer(data_dir, model_dir)
        
    def should_retrain(self):
        """Check if we have enough feedback to justify retraining"""
        if not self.feedback_file.exists():
            return False, "No feedback file found"
        
        lock = FileLock(str(self.feedback_file) + ".lock")
        with lock:
            feedback = json.loads(self.feedback_file.read_text())
        
        feedback_count = len(feedback.get("feedback", []))
        
        # Retrain if we have at least 10 new feedback entries
        MIN_FEEDBACK = 10
        
        if feedback_count < MIN_FEEDBACK:
            return False, f"Need {MIN_FEEDBACK} feedback entries, have {feedback_count}"
        
        return True, f"Ready to retrain with {feedback_count} feedback entries"
    
    def retrain_from_feedback(self):
        """Retrain models using archived data + feedback"""
        print("=" * 70)
        print("AUTOMATED RETRAINING - FEEDBACK LOOP")
        print("=" * 70)
        
        # Check if retraining is needed
        should_train, message = self.should_retrain()
        print(f"\n📊 Status: {message}")
        
        if not should_train:
            print("   Skipping retraining")
            return {"status": "skipped", "reason": message}
        
        # Check if archive exists
        if not self.archive_file.exists():
            print(f"\n⚠️ Archive file not found: {self.archive_file}")
            print("   Using buffer.csv as fallback (limited history)")
            use_archive = False
        else:
            use_archive = True
            print(f"\n✅ Using archived data: {self.archive_file}")
        
        # Load feedback for analysis
        lock = FileLock(str(self.feedback_file) + ".lock")
        with lock:
            feedback = json.loads(self.feedback_file.read_text())
        
        true_positives = sum(1 for f in feedback["feedback"] if f.get("feedback") == "true_positive")
        false_positives = sum(1 for f in feedback["feedback"] if f.get("feedback") == "false_positive")
        
        print(f"\n📈 Feedback Summary:")
        print(f"   True Positives: {true_positives}")
        print(f"   False Positives: {false_positives}")
        if (true_positives + false_positives) > 0:
            accuracy = true_positives/(true_positives+false_positives)*100
            print(f"   Accuracy: {accuracy:.1f}%")
        
        # Adjust contamination based on false positive rate
        if false_positives > true_positives:
            self.trainer.contamination = min(0.05, self.trainer.contamination * 1.5)
            print(f"   ⚠ High false positive rate - increasing contamination to {self.trainer.contamination:.3f}")
        
        # ✅ FIXED: Train directly from archive with lock - NO BUFFER SWAPPING
        if use_archive:
            print(f"\n🔄 Starting retraining with archived data ({self.archive_file.stat().st_size / 1024 / 1024:.2f} MB)...")
            
            try:
                # Train directly from archive file with lock protection
                self.trainer.train_from_archive(self.archive_file)
                
            except Exception as e:
                print(f"\n❌ Retraining failed: {e}")
                return {"status": "failed", "error": str(e)}
        else:
            # Fallback to buffer training
            print("\n🔄 Starting retraining with buffer data (limited history)...")
            try:
                self.trainer.train_all()
            except Exception as e:
                print(f"\n❌ Retraining failed: {e}")
                return {"status": "failed", "error": str(e)}
        
        # Archive feedback after successful retraining
        self._archive_feedback()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "feedback_processed": len(feedback["feedback"]),
            "contamination": self.trainer.contamination,
            "data_source": "archive" if use_archive else "buffer"
        }
    
    def _archive_feedback(self):
        """Move processed feedback to archive with lock protection"""
        archive_file = self.data_dir / "feedback_archive.json"
        archive_lock = FileLock(str(archive_file) + ".lock")
        
        with archive_lock:
            if archive_file.exists():
                archive = json.loads(archive_file.read_text())
            else:
                archive = {"archives": []}
            
            # Add current feedback to archive
            feedback_lock = FileLock(str(self.feedback_file) + ".lock")
            with feedback_lock:
                current = json.loads(self.feedback_file.read_text())
            
            archive["archives"].append({
                "archived_at": datetime.now().isoformat(),
                "feedback": current["feedback"]
            })
            
            # Save archive
            archive_file.write_text(json.dumps(archive, indent=2))
        
        # Clear current feedback with separate lock
        feedback_lock = FileLock(str(self.feedback_file) + ".lock")
        with feedback_lock:
            self.feedback_file.write_text(json.dumps({"feedback": []}, indent=2))
        
        print(f"\n✅ Feedback archived and reset")


def main():
    """Run retraining pipeline"""
    pipeline = RetrainingPipeline()
    result = pipeline.retrain_from_feedback()
    print(f"\n📋 Result: {result}")


if __name__ == "__main__":
    main()