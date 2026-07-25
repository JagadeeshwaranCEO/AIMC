"""
ACR Runtime Tests - Unified API Verification.

Tests the unified ACRRuntime class that consolidates all implementations.
"""

import sys
import os
import numpy as np

runtime_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime')
sys.path.insert(0, runtime_path)


class TestResults:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record(self, name: str, passed: bool, error: str = ""):
        self.total += 1
        if passed:
            self.passed += 1
            print(f"  ✓ {name}")
        else:
            self.failed += 1
            self.errors.append((name, error))
            print(f"  ✗ {name}: {error}")

    def summary(self):
        print(f"\nTotal: {self.total}  Passed: {self.passed}  Failed: {self.failed}")
        if self.failed > 0:
            for name, error in self.errors:
                print(f"  FAIL: {name} -> {error}")
        return self.failed == 0


results = TestResults()


def test_lifecycle():
    print("\n--- Lifecycle Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)
    results.record("create runtime",
                   isinstance(runtime, ACRRuntime))

    assert not runtime.connected
    results.record("initially disconnected",
                   not runtime.get_status()['connected'])

    runtime.connect(rows=4, cols=8, device_type='emulator')
    results.record("connect",
                   runtime.get_status()['connected'] == True and
                   runtime.rows == 4 and runtime.cols == 8)

    runtime.calibrate(num_cells=10)
    results.record("calibrate",
                   runtime.get_status()['calibrated'])

    status = runtime.get_status()
    results.record("get_status returns keys",
                   all(k in status for k in
                       ['connected', 'calibrated', 'programmed',
                        'rows', 'cols', 'seed']))


def test_program_and_read():
    print("\n--- Program/Read Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)
    runtime.connect(rows=4, cols=8, device_type='emulator')

    weights = np.array([[0.5, -0.5, 0.3, -0.3, 0.1, -0.1, 0.8, -0.8]] * 4)
    runtime.program(weights)
    results.record("program returns success",
                   runtime.get_status()['programmed'])

    g = runtime.read()
    results.record("read returns numpy array",
                   isinstance(g, np.ndarray))
    results.record("read shape matches crossbar",
                   g.shape == (4, 8))
    results.record("conductances in [0, 1]",
                   np.all(g >= 0) and np.all(g <= 1))
    results.record("conductances not all equal",
                   not np.allclose(g, g[0, 0]))


def test_vmm():
    print("\n--- VMM Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)
    runtime.connect(rows=4, cols=4, device_type='emulator')

    w = np.eye(4) * 0.5
    runtime.program(w)

    x = np.array([1.0, 0.0, 0.0, 0.0])
    y = runtime.forward_vmm(x)
    results.record("VMM returns correct length",
                   len(y) == 4)


def test_complex_computation():
    print("\n--- Complex Computation Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)

    z = runtime.complex_impedance(1000, 500)
    results.record("complex impedance",
                   isinstance(z, complex))

    mag, phase = runtime.magnitude_phase(z)
    results.record("magnitude positive",
                   mag > 0)
    results.record("phase in range",
                   -math.pi <= phase <= math.pi)

    e = runtime.euler_transform(math.pi)
    results.record("e^(i*pi) = -1",
                   abs(e + 1) < 1e-10)

    e2 = runtime.euler_transform(0)
    results.record("e^(i*0) = 1",
                   abs(e2 - 1) < 1e-10)

    signal = np.sin(np.linspace(0, 2 * math.pi, 64))
    spectrum = runtime.fourier_transform(signal)
    results.record("fourier transform",
                   isinstance(spectrum, np.ndarray) and
                   spectrum.dtype == complex)
    results.record("fourier output length",
                   len(spectrum) == len(signal))

    g0 = complex(1e-6, 0)
    gt = runtime.complex_drift_model(3600, g0, 0.1, 0.01)
    results.record("complex drift model",
                   isinstance(gt, complex) and abs(gt) < 1e-6)


def test_thermodynamic():
    print("\n--- Thermodynamic Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)

    samples = runtime.thermodynamic_sample(
        num_samples=100, potential='harmonic'
    )
    results.record("samples are numpy array",
                   isinstance(samples, np.ndarray))
    results.record("correct number of samples",
                   len(samples) == 100)
    results.record("samples near zero (harmonic well)",
                   abs(np.mean(samples)) < 0.5)

    x2 = runtime.langevin_step(0.0)
    results.record("langevin step returns float",
                   isinstance(x2, (float, np.floating)))

    avg = runtime.boltzmann_average(lambda x: x**2, 500)
    results.record("boltzmann average positive",
                   avg > 0)


def test_neural_ode():
    print("\n--- Neural ODE Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)

    x = np.array([1.0, 0.0])
    y = runtime.neural_ode_forward(x)
    results.record("Neural ODE forward returns array",
                   isinstance(y, np.ndarray))

    h0 = np.array([1.0, 0.0])
    t_span = np.linspace(0, 1, 50)
    traj = runtime.neural_ode_solve(h0, t_span)
    results.record("ODE solve returns trajectory",
                   isinstance(traj, np.ndarray) and len(traj) == 50)


def test_drift():
    print("\n--- Drift Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)
    runtime.connect(rows=4, cols=4, device_type='emulator')

    g_before = runtime.read()
    runtime.step_time(100, power_law=False)
    g_after = runtime.read()
    drifted = not np.allclose(g_before, g_after)
    results.record("exponential drift changes values",
                   drifted)

    runtime.program(np.eye(4))
    g_before = runtime.read().copy()
    runtime.step_time(100, power_law=True)
    g_after = runtime.read()
    drifted = not np.allclose(g_before, g_after)
    results.record("power-law drift changes values",
                   drifted)


def test_predict_drift():
    print("\n--- Predict Drift Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)
    runtime.connect(rows=4, cols=4, device_type='emulator')
    runtime.program(np.eye(4) * 0.5)

    g_predicted = runtime.predict_drift(time_ahead=3600)
    results.record("predict returns numpy array",
                   isinstance(g_predicted, np.ndarray))
    results.record("predict matches crossbar shape",
                   g_predicted.shape == (4, 4))
    results.record("predicted values in [0,1]",
                   np.all(g_predicted >= 0) and np.all(g_predicted <= 1))


def test_energy():
    print("\n--- Energy Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)
    result = runtime.optimize_energy(1e-9)
    results.record("energy returns dict",
                   isinstance(result, dict))


def test_not_connected_errors():
    print("\n--- Error Handling Tests ---")
    from acr_runtime import ACRRuntime

    runtime = ACRRuntime(seed=42)
    errors_caught = 0

    try:
        runtime.program(np.eye(4))
    except RuntimeError:
        errors_caught += 1

    try:
        runtime.read()
    except RuntimeError:
        errors_caught += 1

    try:
        runtime.forward_vmm(np.ones(4))
    except RuntimeError:
        errors_caught += 1

    try:
        runtime.predict_drift()
    except RuntimeError:
        errors_caught += 1

    try:
        runtime.calibrate()
    except RuntimeError:
        errors_caught += 1

    results.record("all 5 pre-connection errors caught",
                   errors_caught == 5)


def test_re_exports():
    print("\n--- Re-export Tests ---")
    from acr_runtime import (
        AnalogCrossbar2D, VirtualConductanceManager,
        ComplexValuedComputation, ThermodynamicComputer,
        NeuralODE
    )

    results.record("AnalogCrossbar2D re-exported",
                   AnalogCrossbar2D is not None)
    results.record("VirtualConductanceManager re-exported",
                   VirtualConductanceManager is not None)
    results.record("ComplexValuedComputation re-exported",
                   ComplexValuedComputation is not None)
    results.record("ThermodynamicComputer re-exported",
                   ThermodynamicComputer is not None)
    results.record("NeuralODE re-exported",
                   NeuralODE is not None)


def test_device_type_enum():
    print("\n--- Device Type Enum Tests ---")
    from acr_runtime import (
        HALDeviceType, RevolutionDeviceType
    )
    results.record("HAL DeviceType has RRAM",
                   HALDeviceType.RRAM.value == 'rram')
    results.record("HAL DeviceType has PCM",
                   HALDeviceType.PCM.value == 'pcm')
    results.record("Revolution DeviceType has RRAM",
                   RevolutionDeviceType.RRAM.value == 'rram')
    results.record("Revolution DeviceType has PHOTONIC",
                   hasattr(RevolutionDeviceType, 'PHOTONIC'))


if __name__ == "__main__":
    import math
    print("=" * 60)
    print("ACR RUNTIME TESTS - Unified API Verification")
    print("=" * 60)

    test_re_exports()
    test_lifecycle()
    test_not_connected_errors()
    test_program_and_read()
    test_vmm()
    test_complex_computation()
    test_thermodynamic()
    test_neural_ode()
    test_drift()
    test_predict_drift()
    test_energy()
    test_device_type_enum()

    success = results.summary()
    sys.exit(0 if success else 1)
