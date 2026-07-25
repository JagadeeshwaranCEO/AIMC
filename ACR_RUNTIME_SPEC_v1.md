# ACR Runtime Specification v1.0

**Version:** 1.0
**Date:** July 26, 2026
**Status:** Draft Specification

---

## 1. Introduction

### 1.1 Purpose

The Analog Compute Runtime (ACR) provides **deterministic software semantics over nondeterministic analog hardware**. Analog memory devices (RRAM, PCM, FeFET) are inherently unreliable: their conductance drifts over time, varies between devices, and responds differently to SET vs RESET pulses. ACR abstracts these non-idealities behind a unified software interface, enabling AI frameworks to execute on analog hardware without hardware expertise.

### 1.2 Scope

This specification defines the ACR runtime architecture, public API, memory model, device abstraction interface, calibration protocol, drift management contract, reliability guarantees, and performance model. It covers the software runtime only — physical hardware interfaces are defined by the HAL (Hardware Abstraction Layer) specification.

### 1.3 Design Tenets

| Tenet | Rationale |
|-------|-----------|
| **Hardware-agnostic** | Same API works across RRAM, PCM, FeFET, and future devices |
| **Deterministic semantics** | Application code should not need to know about drift or noise |
| **Self-adaptive** | Runtime should calibrate itself without prior device knowledge |
| **Modular** | Each runtime service has a single responsibility |
| **Observable** | All internal state is exposed via telemetry |

---

## 2. System Architecture

### 2.1 Layered Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│  PyTorch / NumPy code using ACRRuntime API                   │
├──────────────────────────────────────────────────────────────┤
│                 ACR Runtime (acr_runtime.py)                   │
│  Unified entry point: connect, calibrate, program, read      │
├──────────────────┬───────────────────────────────────────────┤
│  Runtime Core    │  Reliability Services                     │
│  ────────────    │  ─────────────────────                    │
│  · Scheduler      │  · Compensation Tick Coprocessor          │
│  · Device Manager │  · Sparse Probe Calibration               │
│  · ISA Executor   │  · Kalman Drift Tracking                  │
│  · Pulse Compiler │  · Tiki-Taka Asymmetry Correction         │
│  · Profiler       │  · Adaptive Tick Scheduling               │
├──────────────────┴───────────────────────────────────────────┤
│              Hardware Abstraction Layer (HAL)                  │
│  AbstractDevice | RRAMDevice | PCMDevice | FeFETDevice       │
├──────────────────────────────────────────────────────────────┤
│                    Physical Hardware                           │
│  Crossbar array | DAC/ADC | Pulse generators                 │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Module Inventory

| Module | File | Responsibility |
|--------|------|----------------|
| **Unified API** | `acr_runtime.py` | Single entry point, delegates to subsystem |
| **Crossbar Emulator** | `emulator.py` | AnalogCell, AnalogCrossbar2D (VMM, drift) |
| **Virtual Conductance Manager** | `vcm.py` | Weight → conductance mapping |
| **Instruction Set Arch** | `isa.py` | OpCodes, Instruction, InstructionSet |
| **Scheduler** | `scheduler.py` | Instruction queue, maintenance injection |
| **Device Manager** | `device_manager.py` | Tile allocation, health tracking |
| **HAL** | `hal.py` | Device ABC, RRAM/PCM/FeFET impls |
| **Pulse Compiler** | `pulse_compiler.py` | Open-loop pulse sequence planning |
| **Improved Pulse Compiler** | `pulse_compiler_improved.py` | Adaptive pulse width, two-pass |
| **Closed Loop** | `closed_loop.py` | Measure-correct-repeat programming |
| **Sparse Probe** | `sparse_probe.py` | ~5% cell read + tile regression |
| **Kalman Filter** | `kalman_filter.py` | Per-tile drift exponent tracking |
| **Tiki-Taka** | `tiki_taka.py` | Asymmetry symmetry-point estimation |
| **Tick Scheduler** | `tick_scheduler.py` | Adaptive tick interval based on drift |
| **Compensation Tick** | `compensation_tick.py` | Integrates probe+kalman+tiki+tick |
| **Calibration Utilities** | `calibration.py` | Power-law + cell profile fitting |
| **Profiler** | `profiler.py` | Cell characterization via pulses |
| **Adaptive Calibration** | `adaptive_calibration.py` | Self-healing pulse correction |
| **Analog Virtual Memory** | `analog_virtual_memory.py` | Logical→physical page mapping |
| **Optimizer** | `optimizer.py` | Update/refresh/migration decisions |
| **Telemetry** | `telemetry.py` | Event and time-series collection |
| **Fault Injection** | `fault_injection.py` | Stuck-at, sneak path simulation |
| **PyTorch Bridge** | `torch_bridge.py` | nn.Linear on crossbar via scheduler |
| **Analog Training** | `analog_training.py` | Custom autograd for analog backprop |
| **Complex Math** | `acr_revolution.py` | Euler, Fourier, complex drift model |
| **Thermodynamic** | `acr_holy_trinity.py` | Langevin, Neural ODE, Crossbar |

### 2.3 Data Flow

```
Program → VCM (weights→conductance)
         → Crossbar.program_conductances()
         → AnalogCell[].g_norm = target

Read → Crossbar.read_conductances()
     → AnalogCell[].read()
     → numpy array

VMM → Crossbar.forward_vmm(x)
    → y[c] = Σ_r x[r] * G[r][c]

Drift Tick → step_time(dt) | step_time_power_law(dt, nu)
           → AnalogCell[].g_norm *= decay

Calibration → probe cells → read → regress → correct
```

---

## 3. Runtime Lifecycle

### 3.1 State Machine

```
┌──────────┐   connect()    ┌────────────┐   calibrate()    ┌────────────┐
│ UNINIT   │ ────────────→  │ CONNECTED  │ ─────────────→   │ CALIBRATED │
└──────────┘                └────────────┘                  └────────────┘
                                 │                              │
                                 │ program()                    │ program()
                                 ↓                              ↓
                           ┌────────────┐                  ┌────────────┐
                           │ PROGRAMMED │                  │ CALIBRATED │
                           └────────────┘                  │ PROGRAMMED │
                                                            └────────────┘
```

### 3.2 State Table

| State | Allowed Operations | Transitions |
|-------|-------------------|-------------|
| `UNINIT` | None | `connect()` → CONNECTED |
| `CONNECTED` | `calibrate()`, `get_status()` | `calibrate()` → CALIBRATED |
| `CALIBRATED` | `program()`, `read()`, `forward_vmm()`, `calibrate()`, `predict_drift()` | `program()` → CALIBRATED | PROGRAMMED |
| `CALIBRATED | PROGRAMMED` | All operations | — |

### 3.3 Precondition Errors

All mutating operations (`program`, `read`, `forward_vmm`, `predict_drift`, `calibrate`) raise `RuntimeError` if called while in `UNINIT` state.

---

## 4. API Specification

### 4.1 ACRRuntime

```python
class ACRRuntime:
    def __init__(self, seed: int = 42)
```

**seed:** PRNG seed for reproducible cell behavior.

### 4.2 Connection

```python
def connect(
    self,
    rows: int = 8,
    cols: int = 8,
    device_type: str = 'emulator',
    config: Optional[Dict] = None
) -> bool
```

| Parameter | Values | Description |
|-----------|--------|-------------|
| `rows` | >= 1 | Number of crossbar rows (input dimension) |
| `cols` | >= 1 | Number of crossbar columns (output dimension) |
| `device_type` | `'emulator'`, `'rram'`, `'pcm'`, `'fefet'` | Backend device |
| `config` | optional dict | Device-specific configuration |

**Postconditions:** `connected = True`, `rows`, `cols` set. Crossbar allocated.

### 4.3 Calibration

```python
def calibrate(self, num_cells: int = 10) -> Dict
```

Returns calibration summary dict. **Postconditions:** `calibrated = True`.

### 4.4 Status

```python
def get_status(self) -> Dict
```

Returns dict with keys: `connected`, `calibrated`, `programmed`, `rows`, `cols`, `seed`.

### 4.5 Programming

```python
def program(
    self,
    weights: np.ndarray,
    compensate_drift: bool = True
) -> bool
```

| Parameter | Constraint | Description |
|-----------|-----------|-------------|
| `weights` | shape `(rows, cols)` | Weight matrix to program |
| `compensate_drift` | bool | Apply drift pre-compensation |

**Algorithm:**
1. Map weights to conductances: `g = vcm.scale_weights_to_conductance(weights)`
2. Optionally apply drift compensation
3. Write to crossbar: `crossbar.program_conductances(g.T)`
4. Set `programmed = True`

The transpose `.T` is required because the crossbar maps input voltage vector `x` (dimension `rows`) to output current `y = x @ G` where `G` has shape `(rows, cols)`. Weights are stored as `w[output, input]` = shape `(cols, rows)`, so `weights.T` = `(rows, cols)` = crossbar conductance matrix.

### 4.6 Reading

```python
def read(self) -> np.ndarray
```

Returns `np.ndarray` of shape `(rows, cols)` with normalized conductances in `[0, 1]`.

### 4.7 Vector-Matrix Multiplication

```python
def forward_vmm(self, x: np.ndarray) -> np.ndarray
```

| Parameter | Constraint | Description |
|-----------|-----------|-------------|
| `x` | `len(x) == rows` | Input voltage vector |

**Returns:** Output current vector of length `cols`.

**Physical model:** `y[c] = Σ_{r=0}^{rows-1} x[r] * G[r][c]` (Kirchhoff's current law).

### 4.8 Complex-Valued Computation

```python
def euler_transform(self, angle: float) -> complex
def complex_impedance(self, R: float, X: float) -> complex
def magnitude_phase(self, Z: complex) -> Tuple[float, float]
def fourier_transform(self, signal: np.ndarray) -> np.ndarray
def complex_drift_model(self, t: float, G0: complex,
                         nu_real: float, nu_imag: float,
                         t0: float = 1.0) -> complex
```

| Method | Returns | Description |
|--------|---------|-------------|
| `euler_transform` | `complex` | `e^(i*angle) = cos(angle) + i*sin(angle)` |
| `complex_impedance` | `complex` | `Z = R + jX` |
| `magnitude_phase` | `(float, float)` | `(abs(Z), phase(Z))` |
| `fourier_transform` | `np.ndarray[complex]` | Vanilla 1D DFT via Euler |
| `complex_drift_model` | `complex` | `G0 * (t/t0)^(-nu_real - j*nu_imag)` |

### 4.9 Thermodynamic Computing

```python
def thermodynamic_sample(
    self,
    num_samples: int = 1000,
    potential: str = 'harmonic'
) -> np.ndarray

def langevin_step(self, x: float, dt: float = 1e-9) -> float

def boltzmann_average(
    self,
    observable,
    num_samples: int = 10000
) -> float
```

**Langevin equation:** `dX_t = -∇V(X_t)dt + √(2D) dW_t`

| Potential | Formula | Usage |
|-----------|---------|-------|
| `'harmonic'` | `V(x) = 0.5 * k * x²` | Gaussian sampling |
| `'double_well'` | `V(x) = -a*x² + b*x⁴` | Bimodal sampling |
| `'flat'` | `V(x) = 0` | Free diffusion |

### 4.10 Neural ODE

```python
def neural_ode_forward(self, x: np.ndarray) -> np.ndarray
def neural_ode_solve(
    self, h0: np.ndarray, t_span: np.ndarray
) -> np.ndarray
```

**Dynamics:** `dh/dt = f(h, t, θ)` where `f` is a learned neural network with hidden dimension matching `len(h0)`.

**Solvers:** Euler (`method='euler'`), RK4 (`method='rk4'`).

### 4.11 Drift Management

```python
def predict_drift(self, time_ahead: float = 3600.0) -> np.ndarray
def step_time(self, dt: float, power_law: bool = True)
```

**Power-law drift model:** `G(t) = G0 * ((t+dt)/t)^(-nu)` where `nu` is the drift exponent (default 0.01).

**Exponential drift model:** `G(t) = G_baseline + (G0 - G_baseline) * exp(-dt / τ)` where `τ` is per-cell `drift_tau`.

### 4.12 Energy Optimization

```python
def optimize_energy(self, budget: float) -> Dict
```

Returns energy statistics dict. `budget` parameter reserved for future constrained optimization.

---

## 5. Memory Model

### 5.1 Conductance Representation

All conductances are stored as **normalized values** `g ∈ [0, 1]` where 0 represents minimum conductance and 1 represents maximum conductance of the physical device.

```python
# Internal cell state
cell.g_norm  # float in [0, 1]

# Conversion to physical units
g_physical = g_min_phys + g_norm * (g_max_phys - g_min_phys)
```

### 5.2 Weight-to-Conductance Mapping

The `VirtualConductanceManager` maps neural network weights (which can be negative) to conductances (which are non-negative):

```python
def scale_weights_to_conductance(self, weights: np.ndarray) -> np.ndarray:
    """
    Maps weights ∈ [-1, 1] to conductances ∈ [0, 1].
    Uses linear scaling: g = (w - min) / (max - min)
    """
    w_min = weights.min()
    w_max = weights.max()
    if abs(w_max - w_min) < 1e-10:
        return np.full_like(weights, 0.5)
    return (weights - w_min) / (w_max - w_min)
```

**Differential pair mapping** (alternative): `W = G⁺ - G⁻` where two cells store the positive and negative components, extending the range to `[-1, 1]`.

### 5.3 Crossbar Layout

An `M × N` crossbar has `M` rows (input lines) and `N` columns (output lines). The conductance matrix `G` has shape `(M, N)` where `G[i][j]` is the conductance at row `i`, column `j`.

### 5.4 Memory Lifetime

| Phase | Cell State |
|-------|-----------|
| Fabrication | Random g in [0.2, 0.8] |
| After program | Set to target conductance |
| After drift | Decayed toward drift_baseline |
| After compensation | Restored via correction tick |

---

## 6. Device Abstraction

### 6.1 Hardware Abstraction Layer Interface

```python
class AnalogDevice(ABC):
    @abstractmethod
    def read_conductance(self, cell_id: int) -> float: ...
    @abstractmethod
    def write_conductance(self, cell_id: int,
                          target: float) -> bool: ...
    @abstractmethod
    def get_parameters(self) -> Dict: ...
```

### 6.2 Supported Devices

| Device | Drift Model | Write Speed | Energy/Cell | Key Non-ideality |
|--------|-------------|-------------|-------------|-------------------|
| RRAM | Power-law (nu≈0.01) | 50 ns | 0.5 pJ | Write noise, stochastic SET |
| PCM | Power-law (nu≈0.05) | 100 ns | 2.0 pJ | Large drift, crystallization |
| FeFET | Exponential (τ≈1000) | 5 ns | 0.01 pJ | Retention, endurance |

### 6.3 Device Parameters (Per Cell)

| Parameter | Symbol | Range | Description |
|-----------|--------|-------|-------------|
| Gamma (SET) | γ_up | [0.6, 1.8] | SET nonlinearity exponent |
| Gamma (RESET) | γ_down | [0.6, 1.8] | RESET nonlinearity exponent |
| Pulse gain | η | [0.03, 0.09] | Conductance change per pulse |
| Write noise σ | σ_write | [0.05, 0.25] | Cycle-to-cycle noise fraction |
| Read noise σ | σ_read | [0.002, 0.01] | Read noise in normalized units |
| Drift time constant | τ | [50, 400] | Virtual-time drift relaxation |
| Drift baseline | g_base | [0.05, 0.25] | Conductance relaxation target |

Parameters vary per cell at "fabrication time" (device-to-device variation).

---

## 7. Calibration Model

### 7.1 Calibration Protocol

The calibration protocol establishes the mapping between desired conductance and required pulse parameters:

```
Calibrate(cell):
  1. Apply test pulses at multiple amplitudes
  2. Measure conductance response
  3. Fit pulse-response model (power-law or polynomial)
  4. Store correction factors

Correction(cell, target):
  1. Look up cell calibration parameters
  2. Compute required pulse from inverse model
  3. Apply pulse with correction
  4. Verify and iterate if closed-loop
```

### 7.2 Measured Performance

| Mode | Error | Applications |
|------|-------|-------------|
| Open-loop | 3.2% ± 0.4% | Fast approximate programming |
| Closed-loop | 0.07% ± 0.01% | High-precision weight setting |

### 7.3 Sparse Probe Calibration

Instead of reading all M×N cells, reads ~5% (probe set) and uses linear regression to estimate per-tile scale/offset:

```python
def tile_linear_regression(
    probe_readings: np.ndarray,
    probe_targets: np.ndarray
) -> Tuple[float, float]:
    """Returns (scale, offset) to correct the entire tile."""
```

---

## 8. Drift Management

### 8.1 Drift Models

**Power-law (PCM-style):**
```
G(t) = G0 * (t / t0)^(-nu)
```
where:
- `G0` = conductance at reference time `t0`
- `nu` = drift exponent (per-cell, ≈0.01–0.05)

**Exponential (emulator default):**
```
G(t) = g_base + (G0 - g_base) * exp(-t / τ)
```
where:
- `g_base` = drift baseline (per-cell, 0.05–0.25)
- `τ` = time constant (per-cell, 50–400 time units)

### 8.2 Compensation Tick Protocol

The Compensation Tick is a periodic maintenance operation:

```
Every T seconds:
  1. Read probe set (~5% of cells)
  2. Estimate tile-wide correction (scale + offset)
  3. Apply Kalman filter update
  4. Inject asymmetry correction (Tiki-Taka)
  5. Schedule next tick based on drift rate
```

### 8.3 Kalman Filter Specification

**State:** `nu` (drift exponent)
**Observation:** Measured conductance change on probe cells
**Process noise:** `σ_process = 1e-6`
**Measurement noise:** `σ_measurement = 0.01`

```python
class KalmanDriftTracker:
    def predict(self, steps: int = 1) -> float
    def update(self, measurement: float, g_current: float,
               g_initial: float, dt: float)
```

### 8.4 Adaptive Tick Scheduling

Tick interval adjusts based on drift rate:

```python
class AdaptiveTickController:
    def next_interval(self, drift_rate: float) -> float
```

- High drift → shorter interval
- Stable → longer interval
- Range: [`min_tick_interval`, `max_tick_interval`]

---

## 9. Reliability Guarantees

### 9.1 Operational Guarantees

| Guarantee | Condition | Bound |
|-----------|-----------|-------|
| Read accuracy | Without drift | `±σ_read` per cell |
| Read accuracy | After tick | Within 1% of target |
| Program accuracy | Open-loop | ±3.2% of target |
| Program accuracy | Closed-loop | ±0.07% of target |
| Drift bound | Between ticks | <5% deviation |
| Tile availability | Any time | `Allocation succeeds if any tile free` |

### 9.2 Fault Model

| Fault | Detection | Recovery |
|-------|-----------|----------|
| Stuck-at cell | Sparse probe outlier | Remap to spare cell |
| Drift out of bounds | Kalman innovation threshold | Force recalibration |
| Write failure | Verify after write | Retry with adjusted pulse |

### 9.3 Non-Guarantees

The following are NOT guaranteed:
- **Deterministic timing:** Analog operations have variable latency
- **Bit-exact reproducibility:** Noise sources differ between runs
- **Arbitrary precision:** Conductance is continuous, not digital

---

## 10. Performance Model

### 10.1 Operation Latency (Emulator)

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| VMM (forward_vmm) | O(rows × cols) | Software emulation (O(1) in hardware) |
| Program | O(rows × cols) | Per-cell value write |
| Read | O(rows × cols) | Per-cell read |
| Step time | O(rows × cols) | Per-cell drift update |

### 10.2 Energy Model (Simulated)

Based on published device characteristics:

| Device | Energy/VMM (128×128) | Relative to Digital |
|--------|---------------------|-------------------|
| Digital | 16,384 pJ | 1× |
| RRAM | 163.8 pJ | 100× |
| PCM | 655.4 pJ | 25× |
| FeFET | 3.3 pJ | 5000× |

**Note:** These are hardware-level physics, not runtime contribution. Runtime energy overhead is additive and scales with calibration frequency.

### 10.3 Scaling Characteristics

| Dimension | Crossbar Scale | Tested |
|-----------|---------------|--------|
| Rows | 4–784 | Yes |
| Cols | 4–128 | Yes |
| Devices | 1–1000+ | No (emulator limit) |
| Tiles | 1–16 | Yes |

---

## 11. Error Handling

### 11.1 Error Classification

| Error Type | Mechanism | Recovery |
|-----------|-----------|----------|
| Precondition | `RuntimeError` | Fix state (connect/calibrate) |
| Shape mismatch | `ValueError` | Fix dimensions |
| Device failure | Return `False` | Retry or remap |
| Out of tiles | `RuntimeError` | Free tiles or scale down |

### 11.2 Error Codes (Future)

Reserved for future structured error handling:

| Code | Meaning |
|------|---------|
| `E_NO_DEVICE` | No hardware connected |
| `E_NOT_CALIBRATED` | Calibration required |
| `E_SHAPE_MISMATCH` | Weight/crossbar dimension mismatch |
| `E_WRITE_FAILED` | Cell programming failed |
| `E_OUT_OF_TILES` | No free tiles available |

---

## 12. Telemetry Model

### 12.1 Emitted Events

| Event | Payload | Trigger |
|-------|---------|---------|
| `tile_allocated` | tile_id, rows, cols | DeviceManager.allocate_tile |
| `tile_freed` | tile_id | DeviceManager.free_tile |
| `cell_programmed` | tile_id, cell_id, target, actual | Cell write |
| `tick_executed` | tile_id, drift_rate, correction | Compensation tick |
| `calibration_done` | num_cells, mean_error | Calibration complete |
| `drift_predicted` | tile_id, nu, confidence | Kalman prediction |

### 12.2 Storage

Telemetry is stored as JSON with timestamped entries. No streaming or real-time query support in v1.0.

---

## 13. Dependencies and Constraints

### 13.1 Software Dependencies

| Dependency | Version | Usage |
|-----------|---------|-------|
| Python | >= 3.10 | Runtime |
| NumPy | >= 1.24 | Array operations |
| PyTorch | >= 2.0 (optional) | Training bridge |

### 13.2 Import Model

Runtime modules import each other using bare names:

```python
from emulator import AnalogCell
from vcm import VirtualConductanceManager
```

No `pip install -e .` or package setup. Tests add `runtime/` to `sys.path`:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "runtime"))
```

---

## 14. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-26 | Initial specification |

---

## 15. References

1. **emulator.py** — AnalogCell, AnalogCrossbar2D implementation
2. **vcm.py** — VirtualConductanceManager weight mapping
3. **hal.py** — AnalogDevice ABC and device implementations
4. **compensation_tick.py** — CompensationTickCoprocessor
5. **kalman_filter.py** — KalmanDriftTracker specification
6. **sparse_probe.py** — ProbeSetManager, tile_linear_regression
7. **acr_runtime.py** — Unified ACRRuntime class
8. **SCIENTIFIC_POSITIONING.md** — Evidence-based claims
9. **COMPLETION_ANALYSIS.md** — Implementation status tracking
