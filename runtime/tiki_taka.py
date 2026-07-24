"""
AIMC Tiki-Taka Asymmetry Correction

Implements the Tiki-Taka algorithm for correcting asymmetric SET/RESET
behavior in analog memory cells. This is a key component of the
Compensation Tick coprocessor.

Analog cells have asymmetric SET/RESET behavior (gamma_up != gamma_down).
During training, the symmetry point (where SET and RESET have equal effect)
shifts. Tiki-Taka tracks this shift and corrects it.

The algorithm uses paired SET/RESET pulses on probe cells to estimate
the current symmetry point, then applies a digital correction to
re-center the effective symmetry point.
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class TikiTakaState:
    """State for Tiki-Taka correction on a single tile."""
    tile_id: int
    symmetry_point: float = 0.5
    symmetry_estimates: List[float] = None
    correction_scale: float = 1.0
    correction_offset: float = 0.0
    gamma_up: float = 1.0
    gamma_down: float = 1.0
    steps_since_reestimation: int = 0
    reestimation_interval: int = 50
    probe_readings_history: List[Dict] = None

    def __post_init__(self):
        if self.symmetry_estimates is None:
            self.symmetry_estimates = []
        if self.probe_readings_history is None:
            self.probe_readings_history = []


class TikiTakaCorrector:
    """
    Tiki-Taka asymmetry correction with adaptive symmetry-point re-estimation.

    The core insight: instead of correcting each cell individually (expensive),
    we estimate a single per-tile symmetry point and apply a global DAC
    adjustment that re-centers the effective symmetry point.
    """

    def __init__(self, tile_id: int, probe_indices: List[Tuple[int, int]]):
        """
        Args:
            tile_id: Unique identifier for the tile
            probe_indices: List of (row, col) probe cell positions
        """
        self.state = TikiTakaState(tile_id=tile_id)
        self.probe_indices = probe_indices

    def estimate_symmetry_point(self, crossbar) -> float:
        """
        Estimate where the symmetry point is by applying paired
        SET and RESET pulses to probe cells and measuring the response.

        The symmetry point g* satisfies:
          delta_SET(g*) = -delta_RESET(g*)

        For a cell with gamma_up and gamma_down:
          gain * (1 - g*)^gamma_up = gain * (g*)^gamma_down
          (1 - g*)^gamma_up = (g*)^gamma_down
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
                ratio = abs(delta_set) / abs(delta_reset)

                self.state.probe_readings_history.append({
                    'delta_set': delta_set,
                    'delta_reset': delta_reset,
                    'ratio': ratio,
                    'g_before': g_before,
                })

                if delta_set > abs(delta_reset):
                    sym_estimates.append(g_before - 0.05)
                elif abs(delta_reset) > delta_set:
                    sym_estimates.append(g_before + 0.05)
                else:
                    sym_estimates.append(g_before)

        if sym_estimates:
            new_estimate = np.median(sym_estimates)
            self.state.symmetry_estimates.append(new_estimate)

            alpha = 0.3
            self.state.symmetry_point = (
                alpha * new_estimate + (1 - alpha) * self.state.symmetry_point
            )

        return self.state.symmetry_point

    def compute_correction(self, weight_matrix, target_conductances) -> Tuple[float, float]:
        """
        Compute asymmetry correction for the tile.

        The correction adjusts the DAC voltage mapping so that
        the effective symmetry point aligns with the center of
        the conductance range.
        """
        symmetry_offset = self.state.symmetry_point - 0.5

        gamma_ratio = self._estimate_gamma_ratio()
        correction_scale = 1.0 / (1.0 + abs(symmetry_offset) * gamma_ratio)
        correction_offset = -symmetry_offset * 0.5

        self.state.correction_scale = correction_scale
        self.state.correction_offset = correction_offset

        return correction_scale, correction_offset

    def _estimate_gamma_ratio(self) -> float:
        """
        Estimate gamma_up / gamma_down from recent probe data.
        """
        if len(self.state.probe_readings_history) < 2:
            return 1.0

        recent = self.state.probe_readings_history[-10:]
        set_responses = [r['delta_set'] for r in recent]
        reset_responses = [r['delta_reset'] for r in recent]

        if set_responses and reset_responses:
            avg_set = np.mean(np.abs(set_responses))
            avg_reset = np.mean(np.abs(reset_responses))
            if avg_reset > 1e-8:
                self.state.gamma_up = avg_set / avg_reset
                self.state.gamma_down = 1.0
                return avg_set / avg_reset

        return 1.0

    def update_asymmetry_params(self, gamma_up: float, gamma_down: float):
        """
        Update asymmetry parameters from external source.
        """
        self.state.gamma_up = gamma_up
        self.state.gamma_down = gamma_down

    def should_reestimate(self) -> bool:
        """Check if symmetry point should be re-estimated."""
        return (self.state.steps_since_reestimation >=
                self.state.reestimation_interval)

    def mark_reestimated(self):
        """Mark that symmetry point was just re-estimated."""
        self.state.steps_since_reestimation = 0

    def increment_step(self):
        """Increment step counter."""
        self.state.steps_since_reestimation += 1

    def get_state(self) -> Dict:
        """Get current correction state."""
        return {
            'tile_id': self.state.tile_id,
            'symmetry_point': self.state.symmetry_point,
            'correction_scale': self.state.correction_scale,
            'correction_offset': self.state.correction_offset,
            'gamma_up': self.state.gamma_up,
            'gamma_down': self.state.gamma_down,
            'gamma_ratio': self.state.gamma_up / self.state.gamma_down if self.state.gamma_down > 0 else 1.0,
            'steps_since_reestimation': self.state.steps_since_reestimation,
            'num_estimates': len(self.state.symmetry_estimates),
        }

    def get_history(self) -> List[Dict]:
        """Get symmetry point estimation history."""
        return [
            {'estimate': est, 'index': i}
            for i, est in enumerate(self.state.symmetry_estimates)
        ]


class MultiTileTikiTaka:
    """
    Manages Tiki-Taka correction across multiple tiles.
    """

    def __init__(self):
        self.correctors: Dict[int, TikiTakaCorrector] = {}

    def initialize_tile(self, tile_id: int, probe_indices: List[Tuple[int, int]]):
        """Initialize Tiki-Taka for a tile."""
        self.correctors[tile_id] = TikiTakaCorrector(tile_id, probe_indices)

    def estimate_symmetry_point(self, tile_id: int, crossbar) -> float:
        """Estimate symmetry point for a tile."""
        if tile_id not in self.correctors:
            return 0.5
        return self.correctors[tile_id].estimate_symmetry_point(crossbar)

    def compute_correction(self, tile_id: int, weight_matrix, target_conductances) -> Tuple[float, float]:
        """Compute correction for a tile."""
        if tile_id not in self.correctors:
            return 1.0, 0.0
        return self.correctors[tile_id].compute_correction(weight_matrix, target_conductances)

    def should_reestimate(self, tile_id: int) -> bool:
        """Check if a tile needs symmetry re-estimation."""
        if tile_id not in self.correctors:
            return False
        return self.correctors[tile_id].should_reestimate()

    def get_all_states(self) -> Dict[int, Dict]:
        """Get states of all correctors."""
        return {tid: corrector.get_state()
                for tid, corrector in self.correctors.items()}
