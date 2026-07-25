"""
ACR Day 1 - Analog Memory Cell Emulator (software surrogate)

Stands in for real RRAM/PCM/memristor hardware until a physical
device-in-the-loop is wired up. Models, per cell:

  - device-to-device variation   (every cell gets randomized physical params)
  - cycle-to-cycle write noise   (same pulse -> slightly different outcome)
  - read noise                   (reading is noisy, doesn't disturb state)
  - asymmetric saturating update (SET and RESET have different nonlinearity)
  - simplified relaxation drift  (conductance creeps over virtual time)

Conductance is tracked internally as a normalized value g in [0, 1].
g_min_phys / g_max_phys only exist for human-readable display.
"""

import math
import random
import numpy as np


class AnalogCell:
    def __init__(self, cell_id, g_min_phys=1.0, g_max_phys=25.0, seed=None, init_g_norm=None):
        rng = random.Random(seed)
        self.cell_id = cell_id
        self.g_min_phys = g_min_phys
        self.g_max_phys = g_max_phys

        # --- device-to-device variation, fixed at "fabrication" time ---
        self.gamma_up = rng.uniform(0.6, 1.8)            # SET nonlinearity exponent
        self.gamma_down = rng.uniform(0.6, 1.8)          # RESET nonlinearity exponent (independent -> asymmetry)
        self.pulse_gain = rng.uniform(0.03, 0.09)        # normalized conductance change per pulse, pre-nonlinearity
        self.write_noise_std = rng.uniform(0.05, 0.25)   # cycle-to-cycle noise, as a fraction of the pulse step
        self.read_noise_std = rng.uniform(0.002, 0.01)   # read noise, normalized units
        self.drift_tau = rng.uniform(50, 400)            # virtual-time constant for relaxation drift
        self.drift_baseline = rng.uniform(0.05, 0.25)    # conductance the cell relaxes toward over time

        self.g_norm = init_g_norm if init_g_norm is not None else rng.uniform(0.2, 0.8)
        self.t = 0.0
        self._rng = rng

    @staticmethod
    def _clip(x):
        return max(0.0, min(1.0, x))

    def apply_pulse(self, direction, pulse_width=1.0):
        """
        direction: 'SET' (push conductance up) or 'RESET' (push it down).
        pulse_width: relative pulse strength/duration, 1.0 = one standard pulse.
        Returns the realized (noisy) change in normalized conductance.
        """
        if direction not in ("SET", "RESET"):
            raise ValueError("direction must be 'SET' or 'RESET'")

        base_step = self.pulse_gain * pulse_width
        if direction == "SET":
            ideal_delta = base_step * ((1.0 - self.g_norm) ** self.gamma_up)
        else:
            ideal_delta = -base_step * (self.g_norm ** self.gamma_down)

        noise = self._rng.gauss(0.0, self.write_noise_std * base_step)
        realized_delta = ideal_delta + noise
        self.g_norm = self._clip(self.g_norm + realized_delta)
        return realized_delta

    def step_time(self, dt):
        """Advance virtual time by dt, applying simplified relaxation drift."""
        self.t += dt
        decay = math.exp(-dt / self.drift_tau)
        self.g_norm = self._clip(self.drift_baseline + (self.g_norm - self.drift_baseline) * decay)

    def step_time_power_law(self, dt, nu=None):
        """
        Apply power-law drift: G(t) = G0 * ((t0+dt)/t0)^(-nu)

        This models PCM and other devices that show log-time drift.
        Power-law drift is more realistic than exponential decay for
        many analog memory technologies.

        Args:
            dt: Time increment
            nu: Drift exponent (if None, use a default based on cell properties)
        """
        if nu is None:
            nu = 0.01

        if self.t <= 0 or dt <= 0:
            self.t += dt
            return

        t_ratio = (self.t + dt) / self.t
        if t_ratio > 1.0:
            decay = t_ratio ** (-nu)
            self.g_norm = self._clip(self.g_norm * decay)

        self.t += dt

    def read(self, add_noise=True):
        val = self.g_norm
        if add_noise:
            val = self._clip(val + self._rng.gauss(0.0, self.read_noise_std))
        return val

    def read_physical(self, add_noise=True):
        g = self.read(add_noise=add_noise)
        return self.g_min_phys + g * (self.g_max_phys - self.g_min_phys)

    def true_params(self):
        """Ground truth, for debugging only - real hardware would never expose this."""
        return {
            "cell_id": self.cell_id,
            "gamma_up": self.gamma_up,
            "gamma_down": self.gamma_down,
            "pulse_gain": self.pulse_gain,
            "write_noise_std": self.write_noise_std,
            "read_noise_std": self.read_noise_std,
            "drift_tau": self.drift_tau,
            "drift_baseline": self.drift_baseline,
        }


class AnalogCrossbar:
    """A 1D array of analog cells - one row of a future full crossbar."""

    def __init__(self, n_cells, seed=0, **cell_kwargs):
        self.cells = [
            AnalogCell(cell_id=i, seed=seed * 1000 + i, **cell_kwargs)
            for i in range(n_cells)
        ]

    def __getitem__(self, idx):
        return self.cells[idx]

    def __len__(self):
        return len(self.cells)

    def step_time(self, dt):
        for c in self.cells:
            c.step_time(dt)

    def read_all(self, add_noise=True):
        return [c.read(add_noise=add_noise) for c in self.cells]


class AnalogCrossbar2D:
    """
    An M x N 2D array of analog memory cells representing a weight matrix.
    Performs physical Vector-Matrix Multiplication (VMM).
    """
    def __init__(self, rows, cols, seed=42, **cell_kwargs):
        self.rows = rows
        self.cols = cols
        self.grid = [
            [
                AnalogCell(
                    cell_id=r * cols + c,
                    seed=seed * 10000 + r * cols + c,
                    **cell_kwargs
                )
                for c in range(cols)
            ]
            for r in range(rows)
        ]


    def read_matrix(self, add_noise=False):
        """Returns normalized conductance matrix G as a 2D list [rows][cols]."""
        return [[cell.read(add_noise=add_noise) for cell in row] for row in self.grid]

    def program_conductances(self, g_matrix):
        """
        Write conductance values into all cells.

        Args:
            g_matrix: 2D numpy array of normalized conductances in [0, 1]
        """
        for i in range(min(self.rows, g_matrix.shape[0])):
            for j in range(min(self.cols, g_matrix.shape[1])):
                self.grid[i][j].g_norm = float(g_matrix[i, j])

    def read_conductances(self):
        """
        Read current conductance state as numpy matrix.

        Returns:
            2D numpy array of normalized conductances
        """
        g = np.zeros((self.rows, self.cols))
        for i in range(self.rows):
            for j in range(self.cols):
                g[i, j] = self.grid[i][j].g_norm
        return g


    def forward_vmm(self, x_vector, add_noise=True):
        """
        Performs physical Vector-Matrix Multiplication: y = x @ G
        x_vector: list or 1D array of input voltages/activations in [0, 1]
        Returns: output vector y
        """
        if len(x_vector) != self.rows:
            raise ValueError(f"Input vector length {len(x_vector)} doesn't match crossbar rows {self.rows}")


        g_matrix = self.read_matrix(add_noise=add_noise)
        y_out = [0.0] * self.cols


        # Physical accumulation across rows (Kirchhoff's current law)
        for c in range(self.cols):
            col_current = 0.0
            for r in range(self.rows):
                col_current += x_vector[r] * g_matrix[r][c]
            y_out[c] = col_current


        return y_out


    def step_time(self, dt):
        """Advance relaxation drift across all cells in the matrix."""
        for row in self.grid:
            for cell in row:
                cell.step_time(dt)

    def step_time_power_law(self, dt, nu_per_cell=None):
        """
        Apply power-law drift to all cells.

        Args:
            dt: Time increment
            nu_per_cell: Optional 2D array of drift exponents per cell.
                        If None, uses default nu=0.01 for all cells.
        """
        for r in range(self.rows):
            for c in range(self.cols):
                nu = nu_per_cell[r][c] if nu_per_cell else 0.01
                self.grid[r][c].step_time_power_law(dt, nu)

    def read_sparse(self, probe_indices, add_noise=True):
        """
        Read only specific cells (sparse probe read).

        This is the key operation for the Compensation Tick -
        instead of reading all M*N cells, we read only the probe subset.

        Args:
            probe_indices: List of (row, col) tuples to read
            add_noise: Whether to add read noise

        Returns:
            List of (row, col, conductance) tuples
        """
        return [
            (r, c, self.grid[r][c].read(add_noise=add_noise))
            for r, c in probe_indices
        ]

    def read_probe_set(self, probe_indices, add_noise=True):
        """
        Read probe cells and return flat array of readings.

        Args:
            probe_indices: List of (row, col) tuples to read
            add_noise: Whether to add read noise

        Returns:
            Array of conductance readings
        """
        return np.array([
            self.grid[r][c].read(add_noise=add_noise)
            for r, c in probe_indices
        ])

    def get_probe_targets(self, probe_indices):
        """
        Get target (ideal) conductances for probe cells.

        Args:
            probe_indices: List of (row, col) tuples

        Returns:
            Array of target conductances
        """
        return np.array([
            self.grid[r][c].g_norm
            for r, c in probe_indices
        ])


if __name__ == "__main__":
    xbar = AnalogCrossbar(n_cells=8, seed=42)
    print("initial reads:", [round(v, 3) for v in xbar.read_all()])
    for _ in range(5):
        xbar[0].apply_pulse("SET")
    print("cell 0 after 5 SET pulses:", round(xbar[0].read(), 3))
    xbar.step_time(200)
    print("cell 0 after drift (t=200):", round(xbar[0].read(), 3))
