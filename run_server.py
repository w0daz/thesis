# Alternative way to run the server if main.py doesn't work
# Save this as: run_server.py in PROJECT ROOT (not in backend folder)

import uvicorn
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 STARTING IOT ENERGY MONITORING SYSTEM")
    print("=" * 70)
    print("\n📡 Server running at: http://localhost:8000")
    print("📊 Dashboard: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )