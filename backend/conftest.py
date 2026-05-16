"""pytest: backend/ klasörünü import path'e ekler (flat: app, state, copilot...)."""
import sys
from pathlib import Path

# backend/ klasörünü import path'e ekle: state, copilot, app flat import edilir
sys.path.insert(0, str(Path(__file__).parent))
