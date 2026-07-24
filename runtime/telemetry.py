"""
ACR Runtime Telemetry System
Captures and stores runtime metrics for visualization and analysis.

Tracks:
- Tile allocation/deallocation events
- Operation execution counts
- Drift accumulation and refresh events
- Health scores over time
- Instruction queue depths
- End-to-end latency measurements
"""
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class TelemetryEvent:
    """Single telemetry event with timestamp."""
    timestamp: float
    event_type: str
    tile_id: int
    payload: Dict[str, Any] = field(default_factory=dict)


class RuntimeTelemetry:
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: List[TelemetryEvent] = []
        self.start_time = time.time()
        
        # Aggregate metrics
        self.metrics = {
            "total_operations": 0,
            "total_mvm": 0,
            "total_programs": 0,
            "total_refreshes": 0,
            "total_calibrations": 0,
            "total_tiles_allocated": 0,
            "peak_tile_usage": 0,
            "total_drift_compensation": 0,
        }
        
        # Time series data
        self.timeseries = {
            "timestamps": [],
            "tile_usage": [],
            "queue_depth": [],
            "avg_health": [],
            "operations_per_step": [],
        }
        
        # Per-tile tracking
        self.tile_metrics: Dict[int, Dict] = {}

    def record_event(self, event_type: str, tile_id: int, payload: Optional[Dict] = None):
        """Record a telemetry event."""
        event = TelemetryEvent(
            timestamp=time.time() - self.start_time,
            event_type=event_type,
            tile_id=tile_id,
            payload=payload or {}
        )
        
        self.events.append(event)
        
        # Trim if exceeding max
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Update aggregate metrics
        self._update_metrics(event_type, tile_id)
        
        # Update per-tile metrics
        self._update_tile_metrics(event_type, tile_id, payload)

    def _update_metrics(self, event_type: str, tile_id: int):
        """Update aggregate metrics based on event type."""
        if event_type == "MVM":
            self.metrics["total_mvm"] += 1
            self.metrics["total_operations"] += 1
        elif event_type == "PROGRAM":
            self.metrics["total_programs"] += 1
            self.metrics["total_operations"] += 1
        elif event_type == "REFRESH":
            self.metrics["total_refreshes"] += 1
            self.metrics["total_drift_compensation"] += 1
        elif event_type == "CALIBRATE":
            self.metrics["total_calibrations"] += 1
            self.metrics["total_operations"] += 1
        elif event_type == "ALLOC":
            self.metrics["total_tiles_allocated"] += 1
        elif event_type == "FREE":
            self.metrics["total_tiles_allocated"] = max(0, self.metrics["total_tiles_allocated"] - 1)
        
        # Track peak tile usage
        self.metrics["peak_tile_usage"] = max(
            self.metrics["peak_tile_usage"],
            self.metrics["total_tiles_allocated"]
        )

    def _update_tile_metrics(self, event_type: str, tile_id: int, payload: Optional[Dict]):
        """Update per-tile metrics."""
        if tile_id not in self.tile_metrics:
            self.tile_metrics[tile_id] = {
                "total_operations": 0,
                "mvm_count": 0,
                "program_count": 0,
                "refresh_count": 0,
                "health_history": [],
                "drift_accumulated": 0.0,
            }
        
        tile = self.tile_metrics[tile_id]
        tile["total_operations"] += 1
        
        if event_type == "MVM":
            tile["mvm_count"] += 1
        elif event_type == "PROGRAM":
            tile["program_count"] += 1
        elif event_type == "REFRESH":
            tile["refresh_count"] += 1
            tile["drift_accumulated"] = 0.0  # Reset after refresh
        elif event_type == "DRIFT":
            tile["drift_accumulated"] = payload.get("drift", 0.0) if payload else 0.0

    def record_timeseries(self, timestamp: float, tile_usage: int, 
                          queue_depth: int, avg_health: float, ops_count: int):
        """Record time series snapshot."""
        self.timeseries["timestamps"].append(timestamp)
        self.timeseries["tile_usage"].append(tile_usage)
        self.timeseries["queue_depth"].append(queue_depth)
        self.timeseries["avg_health"].append(avg_health)
        self.timeseries["operations_per_step"].append(ops_count)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all telemetry data."""
        return {
            "metrics": self.metrics,
            "timeseries": self.timeseries,
            "tile_metrics": self.tile_metrics,
            "total_events": len(self.events),
            "runtime_duration": time.time() - self.start_time,
        }

    def get_recent_events(self, count: int = 100) -> List[Dict]:
        """Get most recent telemetry events."""
        events = self.events[-count:]
        return [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "tile_id": e.tile_id,
                "payload": e.payload,
            }
            for e in events
        ]

    def export_json(self, filepath: str):
        """Export telemetry data to JSON file."""
        data = self.get_summary()
        # Convert any non-serializable types
        data["events"] = [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "tile_id": e.tile_id,
                "payload": e.payload,
            }
            for e in self.events[-1000:]  # Last 1000 events
        ]
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def print_summary(self):
        """Print human-readable summary."""
        m = self.metrics
        print("\n" + "=" * 60)
        print("ACR Runtime Telemetry Summary")
        print("=" * 60)
        print(f"Runtime Duration: {time.time() - self.start_time:.2f}s")
        print(f"Total Events: {len(self.events)}")
        print(f"\nOperations:")
        print(f"  Total: {m['total_operations']}")
        print(f"  MVM: {m['total_mvm']}")
        print(f"  Program: {m['total_programs']}")
        print(f"  Refresh: {m['total_refreshes']}")
        print(f"  Calibrate: {m['total_calibrations']}")
        print(f"\nTile Management:")
        print(f"  Peak Usage: {m['peak_tile_usage']} tiles")
        print(f"  Drift Compensations: {m['total_drift_compensation']}")
        print("=" * 60)


if __name__ == "__main__":
    telemetry = RuntimeTelemetry()
    
    # Simulate some events
    for i in range(10):
        telemetry.record_event("MVM", tile_id=i % 4, payload={"latency_ms": 0.5})
        telemetry.record_event("PROGRAM", tile_id=i % 4)
    
    telemetry.record_event("REFRESH", tile_id=0)
    telemetry.record_event("CALIBRATE", tile_id=1)
    
    # Simulate timeseries
    for t in range(100):
        telemetry.record_timeseries(
            timestamp=t * 0.01,
            tile_usage=4,
            queue_depth=t % 5,
            avg_health=1.0 - (t * 0.001),
            ops_count=t % 10
        )
    
    telemetry.print_summary()
    telemetry.export_json("/tmp/test_telemetry.json")
    print("\nTelemetry system functional!")
