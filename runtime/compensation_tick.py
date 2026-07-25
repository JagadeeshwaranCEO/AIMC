"""
AIMC Compensation Tick Coprocessor

The Compensation Tick is a lightweight digital coprocessor primitive that
performs online, per-tile asymmetry-and-drift compensation during training
using periodic sparse readout — not per-cell verify-write — achieving stable
convergence at a fraction of the correction overhead.

Three-layer architecture:
  - Analog Layer (The Plant): AnalogCrossbar2D
  - Digital Layer (This): FPGA/MCU holding correction registers,
    pulse modulator, and Tick Scheduler
  - Software Layer (Host): PyTorch training orchestrator

This is the core innovation of Aegis-AIMC.
"""

import math
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import numpy as np

from sparse_probe import ProbeSetManager, tile_linear_regression
from kalman_filter import MultiTileKalmanManager


@dataclass
class TickConfig:
    """Configuration for the Compensation Tick coprocessor."""
    probe_fraction: float = 0.05
    probe_seed: int = 42
    base_tick_interval: float = 10.0
    min_tick_interval: float = 1.0
    max_tick_interval: float = 1000.0
    initial_nu: float = 0.01
    kalman_process_noise: float = 1e-6
    kalman_measurement_noise: float = 0.01
    asymmetry_correction_enabled: bool = True
    reestimation_period: int = 50
    power_law_drift: bool = True


@dataclass
class TileTickState:
    """State for a single tile's Compensation Tick."""
    tile_id: int
    probe_indices: List[Tuple[int, int]]
    target_conductances: np.ndarray
    reference_time: float
    last_tick_time: float
    correction_scale: float = 1.0
    correction_offset: float = 0.0
    last_scale: float = 1.0
    last_offset: float = 0.0
    tick_count: int = 0
    probe_history: List[np.ndarray] = field(default_factory=list)
    probe_times: List[float] = field(default_factory=list)
    gamma_up: float = 1.0
    gamma_down: float = 1.0
    symmetry_point: float = 0.5


@dataclass
class TickResult:
    """Result of a Compensation Tick execution."""
    tile_id: int
    timestamp: float
    probe_readings: np.ndarray
    drift_exponent: float
    scale: float
    offset: float
    correction_scale: float
    correction_offset: float
    kalman_residual: float
    next_interval: float
    probe_fraction: float
    correction_error: float
    symmetry_point: float
    gamma_ratio: float


class TickScheduler:
    """
    Closed-loop adaptive tick scheduling.

    Adapts tick frequency based on measured drift rate:
    - High-drift tiles tick more frequently
    - Stable tiles tick rarely
    - Uncertainty triggers more frequent ticks
    """

    def __init__(self, tile_ids: List[int], base_interval: float = 10.0,
                 min_interval: float = 1.0, max_interval: float = 1000.0):
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval

        self.tile_schedules = {}
        for tid in tile_ids:
            self.tile_schedules[tid] = {
                'next_tick_time': 0.0,
                'current_interval': base_interval,
                'drift_rate_estimate': 0.01,
                'consecutive_stable_ticks': 0,
                'tick_count': 0,
            }

    def compute_next_interval(self, tile_id: int, measured_nu: float,
                              prediction_residual: float) -> float:
        """
        Adapt tick interval based on measured drift exponent and prediction error.

        High nu (fast drift) -> shorter interval (more frequent ticks)
        Low nu (stable) -> longer interval (less frequent ticks)
        High prediction error -> shorter interval (model is uncertain)
        """
        schedule = self.tile_schedules[tile_id]

        drift_factor = self.base_interval / (measured_nu * 100 + 0.1)

        uncertainty_factor = 1.0 / (1.0 + abs(prediction_residual) * 10)

        if abs(prediction_residual) < 0.01:
            schedule['consecutive_stable_ticks'] += 1
        else:
            schedule['consecutive_stable_ticks'] = 0

        stability_factor = 1.0 + min(schedule['consecutive_stable_ticks'] * 0.1, 2.0)

        new_interval = drift_factor * uncertainty_factor * stability_factor
        new_interval = max(self.min_interval, min(self.max_interval, new_interval))

        alpha = 0.3
        schedule['current_interval'] = alpha * new_interval + (1 - alpha) * schedule['current_interval']

        return schedule['current_interval']

    def should_tick(self, tile_id: int, current_time: float) -> bool:
        """Check if a tile is due for a Compensation Tick."""
        schedule = self.tile_schedules[tile_id]
        return current_time >= schedule['next_tick_time']

    def mark_ticked(self, tile_id: int, current_time: float):
        """Record that a tick just occurred and schedule the next one."""
        schedule = self.tile_schedules[tile_id]
        schedule['tick_count'] += 1
        schedule['next_tick_time'] = current_time + schedule['current_interval']

    def get_interval(self, tile_id: int) -> float:
        """Get current tick interval for a tile."""
        return self.tile_schedules[tile_id]['current_interval']

    def get_tick_count(self, tile_id: int) -> int:
        """Get total tick count for a tile."""
        return self.tile_schedules[tile_id]['tick_count']


class TikiTakaCorrector:
    """
    Tiki-Taka asymmetry correction with adaptive symmetry-point re-estimation.

    Analog cells have asymmetric SET/RESET behavior (gamma_up != gamma_down).
    During training, the symmetry point shifts. Tiki-Taka tracks this shift
    and corrects it, triggered by the Compensation Tick.
    """

    def __init__(self, tile_id: int, probe_indices: List[Tuple[int, int]]):
        self.tile_id = tile_id
        self.probe_indices = probe_indices
        self.symmetry_point = 0.5
        self.symmetry_estimates = []
        self.correction_scale = 1.0
        self.correction_offset = 0.0
        self.steps_since_reestimation = 0
        self.reestimation_interval = 50
        self.residual_history = []
        self.gamma_up = 1.0
        self.gamma_down = 1.0

    def estimate_symmetry_point(self, crossbar) -> float:
        """
        Estimate where the symmetry point is by applying paired
        SET and RESET pulses to probe cells and measuring the response.
        """
        sym_estimates = []

        for (r, c) in self.probe_indices[:min(10, len(self.probe_indices))]:
            cell = crossbar.grid[r][c]

            g_before = cell.read(add_noise=False)
            cell.apply_pulse("SET", pulse_width=0.1)
            g_after_set = cell.read(add_noise=False)
            delta_set = g_after_set - g_before

            cell.apply_pulse("RESET", pulse_width=0.1)
            g_after_reset = cell.read(add_noise=False)
            delta_reset = g_after_reset - g_after_set

            if abs(delta_set) > 1e-8 and abs(delta_reset) > 1e-8:
                if delta_set > abs(delta_reset):
                    sym_estimates.append(g_before - 0.05)
                elif abs(delta_reset) > delta_set:
                    sym_estimates.append(g_before + 0.05)
                else:
                    sym_estimates.append(g_before)

        if sym_estimates:
            new_estimate = np.median(sym_estimates)
            self.symmetry_estimates.append(new_estimate)
            alpha = 0.3
            self.symmetry_point = alpha * new_estimate + (1 - alpha) * self.symmetry_point

        return self.symmetry_point

    def compute_correction(self, weight_matrix, target_conductances) -> Tuple[float, float]:
        """
        Compute asymmetry correction for the tile.
        """
        symmetry_offset = self.symmetry_point - 0.5

        gamma_ratio = self._estimate_gamma_ratio()
        correction_scale = 1.0 / (1.0 + abs(symmetry_offset) * gamma_ratio)
        correction_offset = -symmetry_offset * 0.5

        self.correction_scale = correction_scale
        self.correction_offset = correction_offset

        return correction_scale, correction_offset

    def _estimate_gamma_ratio(self) -> float:
        """Estimate gamma_up / gamma_down from recent probe data."""
        if len(self.residual_history) < 2:
            return 1.0

        recent = self.residual_history[-10:]
        set_responses = [r.get('delta_set', 0) for r in recent if 'delta_set' in r]
        reset_responses = [r.get('delta_reset', 0) for r in recent if 'delta_reset' in r]

        if set_responses and reset_responses:
            avg_set = np.mean(np.abs(set_responses))
            avg_reset = np.mean(np.abs(reset_responses))
            if avg_reset > 1e-8:
                return avg_set / avg_reset

        return 1.0

    def update_state(self, gamma_up: float, gamma_down: float):
        """Update asymmetry parameters."""
        self.gamma_up = gamma_up
        self.gamma_down = gamma_down


class CompensationTickCoprocessor:
    """
    The Compensation Tick is a lightweight digital coprocessor primitive.

    It performs online, per-tile asymmetry-and-drift compensation during
    training using periodic sparse readout.
    """

    def __init__(self, device_manager=None, config: Optional[TickConfig] = None):
        self.config = config or TickConfig()
        self.tile_states: Dict[int, TileTickState] = {}

        self.probe_manager = ProbeSetManager(
            probe_fraction=self.config.probe_fraction,
            seed=self.config.probe_seed
        )

        self.kalman_manager = MultiTileKalmanManager(
            initial_nu=self.config.initial_nu,
            process_noise=self.config.kalman_process_noise,
            measurement_noise=self.config.kalman_measurement_noise
        )

        self.tick_scheduler: Optional[TickScheduler] = None

        self.tick_log: List[TickResult] = []
        self.total_ticks = 0
        self.total_probe_reads = 0
        self.total_corrections = 0

    def initialize_tile(self, tile_id: int, crossbar) -> List[Tuple[int, int]]:
        """
        Initialize coprocessor state for a new tile.

        Args:
            tile_id: Unique identifier for the tile
            crossbar: AnalogCrossbar2D instance

        Returns:
            List of probe indices for this tile
        """
        probe_indices = self.probe_manager.initialize_tile(
            tile_id, crossbar.rows, crossbar.cols
        )

        target_conductances = crossbar.get_probe_targets(probe_indices)

        self.kalman_manager.initialize_tile(tile_id)

        tiki_taka = TikiTakaCorrector(tile_id, probe_indices)

        self.tile_states[tile_id] = TileTickState(
            tile_id=tile_id,
            probe_indices=probe_indices,
            target_conductances=target_conductances,
            reference_time=0.0,
            last_tick_time=0.0,
        )

        if self.tick_scheduler is None:
            self.tick_scheduler = TickScheduler(
                tile_ids=[tile_id],
                base_interval=self.config.base_tick_interval,
                min_interval=self.config.min_tick_interval,
                max_interval=self.config.max_tick_interval
            )
        else:
            self.tick_scheduler.tile_schedules[tile_id] = {
                'next_tick_time': 0.0,
                'current_interval': self.config.base_tick_interval,
                'drift_rate_estimate': 0.01,
                'consecutive_stable_ticks': 0,
                'tick_count': 0,
            }

        return probe_indices

    def initialize_tiles(self, crossbars: Dict[int, Any]):
        """
        Initialize multiple tiles at once.

        Args:
            crossbars: Dictionary mapping tile_id to AnalogCrossbar2D
        """
        tile_ids = list(crossbars.keys())
        self.tick_scheduler = TickScheduler(
            tile_ids=tile_ids,
            base_interval=self.config.base_tick_interval,
            min_interval=self.config.min_tick_interval,
            max_interval=self.config.max_tick_interval
        )

        for tile_id, crossbar in crossbars.items():
            self.initialize_tile(tile_id, crossbar)

    def tick(self, tile_id: int, crossbar, current_time: float) -> TickResult:
        """
        Execute one Compensation Tick on a tile.

        This is the core primitive: sparse probe -> estimate -> correct.

        Args:
            tile_id: Tile to tick
            crossbar: AnalogCrossbar2D instance
            current_time: Current simulation time

        Returns:
            TickResult with metrics about what happened
        """
        if tile_id not in self.tile_states:
            raise ValueError(f"Tile {tile_id} not initialized")

        state = self.tile_states[tile_id]
        self.total_ticks += 1

        probe_readings = np.array([
            crossbar.grid[r][c].read(add_noise=True)
            for r, c in state.probe_indices
        ])
        self.total_probe_reads += len(probe_readings)

        state.probe_history.append(probe_readings)
        state.probe_times.append(current_time)

        mean_probe = np.mean(probe_readings)
        self.kalman_manager.predict(tile_id, current_time)
        kalman_residual = self.kalman_manager.update(tile_id, mean_probe, current_time)

        tiki_taka = TikiTakaCorrector(tile_id, state.probe_indices)
        if state.tick_count % self.config.reestimation_period == 0:
            tiki_taka.estimate_symmetry_point(crossbar)

        correction_scale, correction_offset = tiki_taka.compute_correction(
            None, state.target_conductances
        )

        scale, offset = tile_linear_regression(probe_readings, state.target_conductances)

        state.correction_scale = scale
        state.correction_offset = offset
        state.last_scale = scale
        state.last_offset = offset

        nu = self.kalman_manager.get_nu(tile_id)
        new_interval = self.tick_scheduler.compute_next_interval(
            tile_id, nu, kalman_residual
        )
        self.tick_scheduler.mark_ticked(tile_id, current_time)

        state.last_tick_time = current_time
        state.tick_count += 1

        corrected = (probe_readings - offset) / scale
        corrected = np.clip(corrected, 0.0, 1.0)
        correction_error = np.mean(np.abs(corrected - state.target_conductances))

        result = TickResult(
            tile_id=tile_id,
            timestamp=current_time,
            probe_readings=probe_readings,
            drift_exponent=nu,
            scale=scale,
            offset=offset,
            correction_scale=correction_scale,
            correction_offset=correction_offset,
            kalman_residual=kalman_residual,
            next_interval=new_interval,
            probe_fraction=len(state.probe_indices) / (crossbar.rows * crossbar.cols),
            correction_error=correction_error,
            symmetry_point=tiki_taka.symmetry_point,
            gamma_ratio=tiki_taka._estimate_gamma_ratio()
        )

        self.tick_log.append(result)
        self.total_corrections += 1

        return result

    def should_tick(self, tile_id: int, current_time: float) -> bool:
        """Check if a tile is due for a Compensation Tick."""
        if self.tick_scheduler is None:
            return True
        return self.tick_scheduler.should_tick(tile_id, current_time)

    def get_corrected_conductance_matrix(self, tile_id: int, crossbar) -> List[List[float]]:
        """
        Read the full conductance matrix and apply per-tile correction.

        This replaces raw analog reads with corrected reads.
        """
        if tile_id not in self.tile_states:
            return crossbar.read_matrix(add_noise=True)

        state = self.tile_states[tile_id]
        raw_matrix = crossbar.read_matrix(add_noise=True)

        scale = state.correction_scale
        offset = state.correction_offset

        if abs(scale) < 1e-6:
            return raw_matrix

        corrected = [
            [(cell - offset) / scale for cell in row]
            for row in raw_matrix
        ]

        corrected = [
            [max(0.0, min(1.0, cell)) for cell in row]
            for row in corrected
        ]

        return corrected

    def get_drift_exponent(self, tile_id: int) -> float:
        """Get current drift exponent estimate for a tile."""
        return self.kalman_manager.get_nu(tile_id)

    def get_critical_time(self, tile_id: int, threshold: float = 0.1) -> float:
        """Get predicted critical time for a tile."""
        return self.kalman_manager.get_critical_time(tile_id, threshold)

    def get_efficiency_report(self) -> Dict:
        """Get efficiency comparison: sparse probe vs brute-force verify-write."""
        total_probe_reads = self.total_probe_reads
        total_ticks = self.total_ticks

        if total_ticks == 0:
            return {
                'total_ticks': 0,
                'total_probe_reads': 0,
                'probe_fraction': self.config.probe_fraction,
                'speedup_vs_verify_write': 1.0 / self.config.probe_fraction,
                'tiles': len(self.tile_states),
            }

        avg_probe_per_tick = total_probe_reads / total_ticks
        avg_tile_size = np.mean([
            len(state.probe_indices) / self.config.probe_fraction
            for state in self.tile_states.values()
        ]) if self.tile_states else 256

        return {
            'total_ticks': total_ticks,
            'total_probe_reads': total_probe_reads,
            'probe_fraction': self.config.probe_fraction,
            'speedup_vs_verify_write': 1.0 / self.config.probe_fraction,
            'tiles': len(self.tile_states),
            'avg_probe_per_tick': avg_probe_per_tick,
            'avg_tile_size': avg_tile_size,
            'total_correction_ops': self.total_corrections,
        }

    def get_state_summary(self) -> Dict:
        """Get summary of all tile states."""
        summary = {}
        for tile_id, state in self.tile_states.items():
            nu = self.kalman_manager.get_nu(tile_id)
            critical = self.kalman_manager.get_critical_time(tile_id)
            summary[tile_id] = {
                'tick_count': state.tick_count,
                'drift_exponent': nu,
                'critical_time': critical,
                'correction_scale': state.correction_scale,
                'correction_offset': state.correction_offset,
                'symmetry_point': state.symmetry_point,
                'probe_count': len(state.probe_indices),
            }
        return summary
