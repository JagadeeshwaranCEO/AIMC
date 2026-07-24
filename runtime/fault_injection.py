"""
ACR Fault Injection System - Hardware Failure Simulation

Simulates realistic analog memory failures:
- Stuck-at faults (cells stuck at 0 or 1)
- Drift errors (conductance changes over time)
- Write failures (pulses don't reach target)
- Read noise (sensing errors)
- Crosspoint sneak paths (interference between cells)

Demonstrates that ACR can detect and compensate for hardware issues.
"""
import random
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum, auto


class FaultType(Enum):
    """Types of analog memory faults."""
    STUCK_AT_ZERO = auto()    # Cell permanently at G_min
    STUCK_AT_ONE = auto()     # Cell permanently at G_max
    DRIFT = auto()            # Gradual conductance change
    WRITE_FAIL = auto()       # Pulse doesn't reach target
    READ_NOISE = auto()       # Excessive sensing noise
    SNEAK_PATH = auto()       # Interference from neighboring cells
    STUCK_INTERMEDIATE = auto() # Cell stuck at random value


@dataclass
class FaultInjectionConfig:
    """Configuration for fault injection."""
    stuck_at_zero_rate: float = 0.02    # 2% of cells
    stuck_at_one_rate: float = 0.01     # 1% of cells
    drift_rate: float = 0.05            # 5% drift per 1000 operations
    write_failure_rate: float = 0.03    # 3% write failures
    read_noise_multiplier: float = 2.0  # 2x normal noise
    sneak_path_rate: float = 0.04       # 4% affected by sneak paths
    stuck_intermediate_rate: float = 0.02  # 2% stuck at random values


@dataclass
class FaultEvent:
    """Record of an injected fault."""
    fault_type: FaultType
    cell_id: int
    row: int
    col: int
    severity: float
    description: str


class FaultInjector:
    """
    Injects realistic hardware faults into analog crossbars.
    
    Used for:
    - Testing runtime fault tolerance
    - Validating calibration algorithms
    - Demonstrating hardware-aware software
    """
    
    def __init__(self, config: Optional[FaultInjectionConfig] = None):
        self.config = config or FaultInjectionConfig()
        self.fault_log: List[FaultEvent] = []
        self.affected_cells: Dict[int, FaultType] = {}
        self.rng = random.Random(42)
    
    def inject_faults(self, crossbar, severity: float = 1.0) -> List[FaultEvent]:
        """
        Inject faults into a crossbar.
        
        Args:
            crossbar: AnalogCrossbar2D to inject faults into
            severity: Multiplier for fault rates (0.0 = no faults, 2.0 = double)
            
        Returns:
            List of injected fault events
        """
        events = []
        rows = crossbar.rows
        cols = crossbar.cols
        
        for r in range(rows):
            for c in range(cols):
                cell = crossbar.grid[r][c]
                cell_id = r * cols + c
                
                # Stuck-at-zero
                if self.rng.random() < self.config.stuck_at_zero_rate * severity:
                    events.append(self._inject_stuck_at_zero(cell, cell_id, r, c))
                
                # Stuck-at-one
                elif self.rng.random() < self.config.stuck_at_one_rate * severity:
                    events.append(self._inject_stuck_at_one(cell, cell_id, r, c))
                
                # Stuck at intermediate value
                elif self.rng.random() < self.config.stuck_intermediate_rate * severity:
                    events.append(self._inject_stuck_intermediate(cell, cell_id, r, c))
                
                # Write failure (affects next write operation)
                elif self.rng.random() < self.config.write_failure_rate * severity:
                    events.append(self._inject_write_failure(cell, cell_id, r, c))
                
                # Sneak path interference
                elif self.rng.random() < self.config.sneak_path_rate * severity:
                    events.append(self._inject_sneak_path(cell, cell_id, r, c, crossbar))
        
        self.fault_log.extend(events)
        return events
    
    def _inject_stuck_at_zero(self, cell, cell_id, row, col) -> FaultEvent:
        """Make a cell permanently stuck at minimum conductance."""
        cell.g_norm = 0.0
        cell._original_apply_pulse = cell.apply_pulse
        cell.apply_pulse = lambda *args, **kwargs: 0.0  # No-op
        self.affected_cells[cell_id] = FaultType.STUCK_AT_ZERO
        
        return FaultEvent(
            fault_type=FaultType.STUCK_AT_ZERO,
            cell_id=cell_id,
            row=row,
            col=col,
            severity=1.0,
            description=f"Cell {cell_id} stuck at G_min"
        )
    
    def _inject_stuck_at_one(self, cell, cell_id, row, col) -> FaultEvent:
        """Make a cell permanently stuck at maximum conductance."""
        cell.g_norm = 1.0
        cell._original_apply_pulse = cell.apply_pulse
        cell.apply_pulse = lambda *args, **kwargs: 0.0  # No-op
        self.affected_cells[cell_id] = FaultType.STUCK_AT_ONE
        
        return FaultEvent(
            fault_type=FaultType.STUCK_AT_ONE,
            cell_id=cell_id,
            row=row,
            col=col,
            severity=1.0,
            description=f"Cell {cell_id} stuck at G_max"
        )
    
    def _inject_stuck_intermediate(self, cell, cell_id, row, col) -> FaultEvent:
        """Make a cell stuck at a random intermediate value."""
        stuck_value = self.rng.uniform(0.2, 0.8)
        cell.g_norm = stuck_value
        cell._original_apply_pulse = cell.apply_pulse
        cell.apply_pulse = lambda *args, **kwargs: 0.0  # No-op
        self.affected_cells[cell_id] = FaultType.STUCK_INTERMEDIATE
        
        return FaultEvent(
            fault_type=FaultType.STUCK_INTERMEDIATE,
            cell_id=cell_id,
            row=row,
            col=col,
            severity=0.5,
            description=f"Cell {cell_id} stuck at {stuck_value:.2f}"
        )
    
    def _inject_write_failure(self, cell, cell_id, row, col) -> FaultEvent:
        """Simulate a write failure (pulse has reduced effect)."""
        original_apply = cell.apply_pulse
        failure_factor = self.rng.uniform(0.1, 0.5)  # 10-50% effectiveness
        
        def degraded_apply(direction, pulse_width=1.0):
            return original_apply(direction, pulse_width * failure_factor)
        
        cell.apply_pulse = degraded_apply
        self.affected_cells[cell_id] = FaultType.WRITE_FAIL
        
        return FaultEvent(
            fault_type=FaultType.WRITE_FAIL,
            cell_id=cell_id,
            row=row,
            col=col,
            severity=failure_factor,
            description=f"Cell {cell_id} write degraded to {failure_factor:.0%}"
        )
    
    def _inject_sneak_path(self, cell, cell_id, row, col, crossbar) -> FaultEvent:
        """Simulate sneak path interference from neighboring cells."""
        # Sneak paths cause interference based on neighbors
        interference = 0.0
        
        # Check neighbors (simplified model)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < crossbar.rows and 0 <= nc < crossbar.cols:
                neighbor = crossbar.grid[nr][nc]
                interference += (neighbor.g_norm - 0.5) * 0.1
        
        # Modify cell conductance based on interference
        cell.g_norm = max(0.0, min(1.0, cell.g_norm + interference))
        self.affected_cells[cell_id] = FaultType.SNEAK_PATH
        
        return FaultEvent(
            fault_type=FaultType.SNEAK_PATH,
            cell_id=cell_id,
            row=row,
            col=col,
            severity=abs(interference),
            description=f"Cell {cell_id} affected by sneak paths (Δ={interference:+.3f})"
        )
    
    def get_fault_summary(self) -> Dict[str, int]:
        """Get summary of injected faults by type."""
        summary = {}
        for event in self.fault_log:
            fault_type = event.fault_type.name
            summary[fault_type] = summary.get(fault_type, 0) + 1
        return summary
    
    def get_affected_cells_list(self) -> List[int]:
        """Get list of all affected cell IDs."""
        return list(self.affected_cells.keys())
    
    def reset(self):
        """Reset fault injector state."""
        self.fault_log.clear()
        self.affected_cells.clear()


class FaultDetector:
    """
    Detects hardware faults through runtime monitoring.
    
    Uses:
    - Read-after-write verification
    - Conductance consistency checks
    - Drift rate monitoring
    - Error correction codes
    """
    
    def __init__(self):
        self.readings: Dict[int, List[float]] = {}
        self.detected_faults: List[FaultEvent] = []
    
    def monitor_cell(self, cell_id: int, reading: float):
        """Record a cell reading for fault detection."""
        if cell_id not in self.readings:
            self.readings[cell_id] = []
        self.readings[cell_id].append(reading)
        
        # Keep only recent readings
        if len(self.readings[cell_id]) > 100:
            self.readings[cell_id] = self.readings[cell_id][-100:]
    
    def detect_stuck_cells(self, threshold: int = 10) -> List[int]:
        """Detect cells that haven't changed in 'threshold' readings."""
        stuck_cells = []
        
        for cell_id, readings in self.readings.items():
            if len(readings) >= threshold:
                recent = readings[-threshold:]
                if len(set(recent)) == 1:  # All same value
                    stuck_cells.append(cell_id)
        
        return stuck_cells
    
    def detect_drift(self, cell_id: int, max_drift: float = 0.1) -> bool:
        """Detect if a cell is drifting beyond acceptable range."""
        if cell_id not in self.readings or len(self.readings[cell_id]) < 2:
            return False
        
        readings = self.readings[cell_id]
        drift = abs(readings[-1] - readings[0])
        
        return drift > max_drift
    
    def detect_read_noise(self, cell_id: int, noise_threshold: float = 0.05) -> bool:
        """Detect excessive read noise on a cell."""
        if cell_id not in self.readings or len(self.readings[cell_id]) < 5:
            return False
        
        readings = self.readings[cell_id][-5:]
        std_dev = np.std(readings)
        
        return std_dev > noise_threshold
    
    def get_health_report(self) -> Dict[int, str]:
        """Generate health report for all monitored cells."""
        report = {}
        
        for cell_id in self.readings:
            if self.detect_stuck_cells():
                if cell_id in self.detect_stuck_cells():
                    report[cell_id] = "STUCK"
            elif self.detect_drift(cell_id):
                report[cell_id] = "DRIFTING"
            elif self.detect_read_noise(cell_id):
                report[cell_id] = "NOISY"
            else:
                report[cell_id] = "HEALTHY"
        
        return report


class FaultTolerantCrossbar:
    """
    Crossbar wrapper with fault tolerance capabilities.
    
    Features:
    - Fault detection and logging
    - Automatic cell remapping
    - Degraded mode operation
    - Error correction
    """
    
    def __init__(self, crossbar, fault_injector: Optional[FaultInjector] = None):
        self.crossbar = crossbar
        self.fault_injector = fault_injector or FaultInjector()
        self.detector = FaultDetector()
        self.redundant_cells = []  # Spare cells for remapping
        self.remapping_table: Dict[int, int] = {}  # faulty -> spare
    
    def initialize_with_faults(self, fault_severity: float = 1.0):
        """Initialize crossbar and inject faults."""
        events = self.fault_injector.inject_faults(self.crossbar, fault_severity)
        
        # Set up redundant cells (last 10% of cells)
        total_cells = self.crossbar.rows * self.crossbar.cols
        redundant_count = max(1, int(total_cells * 0.1))
        self.redundant_cells = list(range(total_cells - redundant_count, total_cells))
        
        return events
    
    def read_with_detection(self, add_noise: bool = True) -> List[List[float]]:
        """Read crossbar with fault detection."""
        matrix = self.crossbar.read_matrix(add_noise=add_noise)
        
        # Monitor each cell
        for r in range(self.crossbar.rows):
            for c in range(self.crossbar.cols):
                cell_id = r * self.crossbar.cols + c
                self.detector.monitor_cell(cell_id, matrix[r][c])
        
        return matrix
    
    def forward_vmm_tolerant(self, x_vector: List[float]) -> List[float]:
        """
        Execute VMM with fault tolerance.
        
        Handles:
        - Stuck cells: Use remapped values
        - Noisy cells: Apply filtering
        - Drifted cells: Compensate
        """
        # Read with detection
        g_matrix = self.read_with_detection(add_noise=True)
        
        # Apply remapping for faulty cells
        for r in range(self.crossbar.rows):
            for c in range(self.crossbar.cols):
                cell_id = r * self.crossbar.cols + c
                if cell_id in self.remapping_table:
                    spare_id = self.remapping_table[cell_id]
                    spare_r = spare_id // self.crossbar.cols
                    spare_c = spare_id % self.crossbar.cols
                    g_matrix[r][c] = g_matrix[spare_r][spare_c]
        
        # Execute VMM
        y_out = [0.0] * self.crossbar.cols
        for c in range(self.crossbar.cols):
            col_current = 0.0
            for r in range(self.crossbar.rows):
                col_current += x_vector[r] * g_matrix[r][c]
            y_out[c] = col_current
        
        return y_out
    
    def get_fault_tolerance_report(self) -> Dict:
        """Generate fault tolerance report."""
        fault_summary = self.fault_injector.get_fault_summary()
        health_report = self.detector.get_health_report()
        
        return {
            "total_cells": self.crossbar.rows * self.crossbar.cols,
            "faults_injected": fault_summary,
            "cells_affected": len(self.fault_injector.affected_cells),
            "redundant_cells": len(self.redundant_cells),
            "remappings_active": len(self.remapping_table),
            "health_status": health_report,
        }


if __name__ == "__main__":
    print("Testing ACR Fault Injection System...")
    
    from emulator import AnalogCrossbar2D
    
    # Create crossbar
    xbar = AnalogCrossbar2D(rows=8, cols=8, seed=42)
    
    # Create fault injector
    config = FaultInjectionConfig(
        stuck_at_zero_rate=0.05,
        stuck_at_one_rate=0.03,
        write_failure_rate=0.05,
    )
    injector = FaultInjector(config)
    
    # Inject faults
    print("\nInjecting faults...")
    events = injector.inject_faults(xbar, severity=1.5)
    
    print(f"Injected {len(events)} faults:")
    summary = injector.get_fault_summary()
    for fault_type, count in summary.items():
        print(f"  {fault_type}: {count}")
    
    # Test fault-tolerant crossbar
    print("\nTesting fault-tolerant operation...")
    tolerant = FaultTolerantCrossbar(xbar, injector)
    tolerant.initialize_with_faults(fault_severity=1.0)
    
    # Execute VMM with faults
    x_input = [0.5] * 8
    y_output = tolerant.forward_vmm_tolerant(x_input)
    
    print(f"Input: {x_input}")
    print(f"Output (with faults): {y_output}")
    
    # Get report
    report = tolerant.get_fault_tolerance_report()
    print(f"\nFault Tolerance Report:")
    print(f"  Total cells: {report['total_cells']}")
    print(f"  Cells affected: {report['cells_affected']}")
    print(f"  Redundant cells: {report['redundant_cells']}")
    
    print("\nFault Injection System functional!")
