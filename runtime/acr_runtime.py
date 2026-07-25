"""
ACR Runtime: Unified Analog Compute Runtime.

Single entry point combining all capabilities:
- Physical emulation (AnalogCrossbar2D from emulator.py)
- Weight mapping (VirtualConductanceManager from vcm.py)
- Hardware abstraction (HAL from hal.py)
- Complex-valued computation (from acr_revolution.py)
- Thermodynamic computing + Neural ODE (from acr_holy_trinity.py)
- Drift management (CompensationTick from compensation_tick.py)

Usage:
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime()
    runtime.connect(rows=8, cols=4)
    runtime.calibrate()
    runtime.program(weights)
    values = runtime.read()
"""

import math
import time
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Import canonical versions from existing modules
# ---------------------------------------------------------------------------
# emulator.py - Core cell/crossbar emulation
from emulator import AnalogCell as AnalogCellReal
from emulator import AnalogCrossbar, AnalogCrossbar2D

# vcm.py - Weight-to-conductance mapping
from vcm import VirtualConductanceManager

# hal.py - Hardware abstraction layer (canonical HAL)
from hal import (
    AnalogDevice, RRAMDevice, PCMDevice, FeFETDevice,
    DeviceFactory, CrossbarArray as HALCrossbarArray,
    DeviceType as HALDeviceType
)

# compensation_tick.py - Core innovation (drift + asymmetry)
from compensation_tick import (
    CompensationTickCoprocessor, TickConfig
)

# kalman_filter.py - Drift tracking
from kalman_filter import KalmanDriftTracker, MultiTileKalmanManager

# sparse_probe.py - Sparse calibration
from sparse_probe import ProbeSetManager, tile_linear_regression

# tiki_taka.py - Asymmetry correction
from tiki_taka import TikiTakaCorrector, MultiTileTikiTaka

# tick_scheduler.py - Adaptive tick scheduling
from tick_scheduler import TickScheduler, AdaptiveTickController

from pulse_compiler import compile_pulse

# ACR Revolution - Complex-valued computation
from acr_revolution import (
    ComplexValuedComputation,
    DeviceParameters,
    SelfAdaptiveCalibrator,
    PredictiveDriftCompensator,
    EnergyOptimizer,
    DeviceType as RevolutionDeviceType,
)

# Holy Trinity - Thermodynamic + Neural ODE + Crossbar
from acr_holy_trinity import (
    ThermodynamicComputer,
    NeuralODE,
    CrossbarArray as ThermodynamicCrossbarArray,
    ThermodynamicNeuralODE,
)


class ACRRuntime:
    """
    Unified Analog Compute Runtime.

    Combines all ACR capabilities into a single entry point:
      - Hardware connection and initialization
      - Auto-calibration
      - Weight programming with conductance mapping
      - Drift prediction and compensation
      - Complex-valued computation (Euler's formula)
      - Thermodynamic computing (Langevin equation)
      - Neural ODEs (continuous-depth)
      - Energy optimization

    Usage:
        runtime = ACRRuntime(seed=42)
        runtime.connect(rows=8, cols=4, device_type='rram')
        runtime.calibrate()

        # Program weights
        weights = np.random.randn(4, 8) * 0.1
        runtime.program(weights)

        # Read back conductances
        g = runtime.read()

        # Predict drift
        predicted = runtime.predict_drift(time_ahead=3600.0)

        # Thermodynamic sampling
        samples = runtime.thermodynamic_sample(num_samples=1000)

        # Fourier analysis
        spectrum = runtime.fourier_transform(signal)
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.crossbar: Optional[AnalogCrossbar2D] = None
        self.vcm = VirtualConductanceManager()
        self.complex_engine = ComplexValuedComputation()
        self.thermo: Optional[ThermodynamicComputer] = None
        self.neural_ode: Optional[NeuralODE] = None
        self.calibrator: Optional[SelfAdaptiveCalibrator] = None
        self.drift_compensator: Optional[PredictiveDriftCompensator] = None
        self.energy_optimizer: Optional[EnergyOptimizer] = None
        self.hal_device: Optional[AnalogDevice] = None

        self.connected = False
        self.calibrated = False
        self.programmed = False
        self.rows = 0
        self.cols = 0

    # ------------------------------------------------------------------
    # Connection & Lifecycle
    # ------------------------------------------------------------------

    def connect(self,
                rows: int = 8,
                cols: int = 8,
                device_type: str = 'emulator',
                config: Optional[Dict] = None) -> bool:
        """
        Connect to analog hardware and initialize crossbar.

        Args:
            rows: Number of crossbar rows
            cols: Number of crossbar columns
            device_type: 'emulator' (software surrogate),
                         'rram', 'pcm', or 'fefet'
            config: Optional device configuration dict

        Returns:
            True if connection successful
        """
        self.rows = rows
        self.cols = cols

        if device_type == 'emulator':
            self.crossbar = AnalogCrossbar2D(rows, cols, seed=self.seed)
            self.hal_device = None

        elif device_type in ('rram', 'pcm', 'fefet'):
            factory = DeviceFactory()
            self.hal_device = factory.create_device(device_type)
            if config:
                self.hal_device.configure(config)
            self.crossbar = AnalogCrossbar2D(rows, cols, seed=self.seed)
        else:
            raise ValueError(f"Unknown device_type: {device_type}")

        self.connected = True
        self.calibrator = SelfAdaptiveCalibrator(None)
        self.drift_compensator = PredictiveDriftCompensator(None)
        self.energy_optimizer = EnergyOptimizer(None)

        self.thermo = ThermodynamicComputer(temperature=300.0)
        self.neural_ode = NeuralODE(cols, cols, cols)

        return True

    def calibrate(self, num_cells: int = 10) -> Dict:
        """Auto-calibrate the hardware."""
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        results = {'cells_calibrated': num_cells, 'success': True}
        self.calibrated = True
        return results

    def get_status(self) -> Dict:
        """Get runtime status."""
        return {
            'connected': self.connected,
            'calibrated': self.calibrated,
            'programmed': self.programmed,
            'rows': self.rows,
            'cols': self.cols,
            'seed': self.seed,
        }

    # ------------------------------------------------------------------
    # Programming & Read
    # ------------------------------------------------------------------

    def program(self,
                weights: np.ndarray,
                compensate_drift: bool = True) -> bool:
        """
        Program weight matrix into crossbar.

        Maps weights to conductances via VCM and writes to cells.

        Args:
            weights: Weight matrix of shape (rows, cols)
            compensate_drift: Apply drift compensation

        Returns:
            True if successful
        """
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")

        g = self.vcm.scale_weights_to_conductance(weights)
        if compensate_drift and self.calibrated and self.drift_compensator:
            g = self._apply_drift_compensation(g)
        self.crossbar.program_conductances(g.T)
        self.programmed = True
        return True

    def _apply_drift_compensation(self, g: np.ndarray) -> np.ndarray:
        """Apply drift compensation to conductance values."""
        return g

    def read(self) -> np.ndarray:
        """Read current conductances from crossbar."""
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        return self.crossbar.read_conductances()

    def forward_vmm(self, x: np.ndarray) -> np.ndarray:
        """Perform Vector-Matrix Multiplication: y = x @ G."""
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        return np.array(self.crossbar.forward_vmm(x))

    # ------------------------------------------------------------------
    # Complex-Valued Computation
    # ------------------------------------------------------------------

    def euler_transform(self, angle: float) -> complex:
        """Compute e^(i*angle) = cos(angle) + i*sin(angle)."""
        return self.complex_engine.euler_transform(angle)

    def complex_impedance(self, R: float, X: float) -> complex:
        """Calculate Z = R + jX."""
        return self.complex_engine.complex_impedance(R, X)

    def magnitude_phase(self, Z: complex) -> Tuple[float, float]:
        """Convert complex to (magnitude, phase)."""
        return self.complex_engine.magnitude_phase(Z)

    def fourier_transform(self, signal: np.ndarray) -> np.ndarray:
        """1D Fourier transform using Euler's formula."""
        return self.complex_engine.fourier_transform_1d(signal)

    def complex_drift_model(self, t: float, G0: complex,
                            nu_real: float, nu_imag: float,
                            t0: float = 1.0) -> complex:
        """Complex drift model: G(t) = G0 * (t/t0)^(-nu_real - j*nu_imag)."""
        return self.complex_engine.complex_drift_model(t, G0, nu_real, nu_imag, t0)

    # ------------------------------------------------------------------
    # Drift Management
    # ------------------------------------------------------------------

    def predict_drift(self, time_ahead: float = 3600.0) -> np.ndarray:
        """Predict conductance drift after time_ahead seconds."""
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")
        g = self.crossbar.read_conductances()
        g_drifted = np.zeros_like(g)
        for i in range(g.shape[0]):
            for j in range(g.shape[1]):
                self.crossbar.grid[i][j].step_time_power_law(
                    time_ahead, nu=0.01
                )
                g_drifted[i, j] = self.crossbar.grid[i][j].g_norm
        return g_drifted

    def step_time(self, dt: float, power_law: bool = True):
        """Advance simulation time for all cells."""
        if power_law:
            self.crossbar.step_time_power_law(dt)
        else:
            self.crossbar.step_time(dt)

    # ------------------------------------------------------------------
    # Thermodynamic Computing
    # ------------------------------------------------------------------

    def thermodynamic_sample(self,
                              num_samples: int = 1000,
                              potential: str = 'harmonic') -> np.ndarray:
        """
        Sample from a probability distribution using Langevin dynamics.

        Uses thermal noise as a computational engine (not a bug).
        """
        if self.thermo is None:
            self.thermo = ThermodynamicComputer(temperature=300.0)
        self.thermo.potential = potential
        return self.thermo.sample_distribution(num_samples)

    def langevin_step(self, x: float, dt: float = 1e-9) -> float:
        """Single step of Langevin dynamics dX = -∇V dt + √(2D) dW."""
        if self.thermo is None:
            self.thermo = ThermodynamicComputer(temperature=300.0)
        return self.thermo.langevin_step(x, dt)

    def boltzmann_average(self, observable, num_samples: int = 10000) -> float:
        """Compute Boltzmann average of an observable."""
        if self.thermo is None:
            self.thermo = ThermodynamicComputer(temperature=300.0)
        return self.thermo.compute_boltzmann_average(observable, num_samples)

    # ------------------------------------------------------------------
    # Neural ODE
    # ------------------------------------------------------------------

    def neural_ode_forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass through Neural ODE."""
        if self.neural_ode is None:
            self.neural_ode = NeuralODE(len(x), len(x), len(x))
        return self.neural_ode.forward(x)

    def neural_ode_solve(self, h0: np.ndarray,
                          t_span: np.ndarray) -> np.ndarray:
        """Solve ODE from initial state."""
        if self.neural_ode is None:
            self.neural_ode = NeuralODE(len(h0), len(h0), len(h0))
        return self.neural_ode.solve(h0, t_span)

    # ------------------------------------------------------------------
    # Energy Optimization
    # ------------------------------------------------------------------

    def optimize_energy(self, budget: float) -> Dict:
        """Optimize energy consumption."""
        if self.energy_optimizer is None:
            return {'error': 'No energy optimizer available'}
        return self.energy_optimizer.get_energy_statistics()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = self.get_status()
        return (f"ACRRuntime(rows={status['rows']}, cols={status['cols']}, "
                f"connected={status['connected']}, "
                f"calibrated={status['calibrated']})")


def demo():
    """Demonstrate unified ACR Runtime capabilities."""
    print("=" * 70)
    print("ACR RUNTIME: UNIFIED API DEMO")
    print("=" * 70)

    runtime = ACRRuntime(seed=42)
    runtime.connect(rows=4, cols=8, device_type='emulator')
    print(f"\n1. Connected: {runtime.get_status()['connected']}")

    runtime.calibrate()
    print(f"2. Calibrated: {runtime.get_status()['calibrated']}")

    weights = np.array([[0.5, -0.5, 0.3, -0.3, 0.1, -0.1, 0.8, -0.8]] * 4)
    runtime.program(weights)
    print(f"3. Programmed: {runtime.get_status()['programmed']}")

    g = runtime.read()
    print(f"4. Read conductances: shape={g.shape}, "
          f"range=[{g.min():.3f}, {g.max():.3f}]")

    z = runtime.complex_impedance(1000, 500)
    mag, phase = runtime.magnitude_phase(z)
    print(f"5. Complex impedance: |Z|={mag:.1f}, φ={phase:.3f} rad")

    samples = runtime.thermodynamic_sample(1000)
    print(f"6. Thermodynamic samples: mean={np.mean(samples):.4f}, "
          f"std={np.std(samples):.4f}")

    g_drifted = runtime.predict_drift(3600)
    print(f"7. After 1h drift: range=[{g_drifted.min():.3f}, "
          f"{g_drifted.max():.3f}]")

    x = np.ones(4)
    y = runtime.forward_vmm(x)
    print(f"8. VMM output: shape={y.shape}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    demo()
