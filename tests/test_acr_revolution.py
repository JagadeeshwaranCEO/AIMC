"""
ACR Revolution: Comprehensive Test Suite

Tests for the revolutionary ACR architecture including:
- Complex-valued computation
- Euler-based impedance modeling
- Self-adaptive calibration
- Universal hardware abstraction
- Predictive drift compensation
- Energy optimization
- Developer API

Author: Jagadeeshwaran E (Team Lead)
Date: July 2026
"""

import sys
import os
import math
import cmath
import numpy as np

# Add runtime to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime'))

from acr_revolution import (
    ComplexValuedComputation,
    DeviceType,
    DeviceParameters,
    AnalogCell,
    RRAM_HAL,
    SelfAdaptiveCalibrator,
    PredictiveDriftCompensator,
    ComplexKalmanTracker,
    EnergyOptimizer,
    ACR
)


class TestResults:
    """Track test results."""
    
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
        print("\n" + "=" * 70)
        print(f"RESULTS: {self.passed}/{self.total} tests passed")
        if self.failed > 0:
            print(f"FAILED: {self.failed}")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print("=" * 70)
        return self.failed == 0


def test_complex_computation():
    """Test complex-valued computation engine."""
    print("\n1. Testing Complex-Valued Computation Engine")
    print("-" * 50)
    
    results = TestResults()
    engine = ComplexValuedComputation()
    
    # Test Euler's formula
    try:
        # e^(i*0) = 1
        result = engine.euler_transform(0)
        expected = 1 + 0j
        results.record(
            "Euler transform (angle=0)",
            abs(result - expected) < 1e-10,
            f"Got {result}, expected {expected}"
        )
        
        # e^(i*pi) = -1
        result = engine.euler_transform(math.pi)
        expected = -1 + 0j
        results.record(
            "Euler transform (angle=pi)",
            abs(result - expected) < 1e-10,
            f"Got {result}, expected {expected}"
        )
        
        # e^(i*pi/2) = i
        result = engine.euler_transform(math.pi / 2)
        expected = 0 + 1j
        results.record(
            "Euler transform (angle=pi/2)",
            abs(result - expected) < 1e-10,
            f"Got {result}, expected {expected}"
        )
    except Exception as e:
        results.record("Euler transform", False, str(e))
    
    # Test complex impedance
    try:
        Z = engine.complex_impedance(1000, 500)
        expected = 1000 + 500j
        results.record(
            "Complex impedance",
            Z == expected,
            f"Got {Z}, expected {expected}"
        )
    except Exception as e:
        results.record("Complex impedance", False, str(e))
    
    # Test magnitude/phase extraction
    try:
        Z = 3 + 4j
        mag, phase = engine.magnitude_phase(Z)
        results.record(
            "Magnitude extraction",
            abs(mag - 5.0) < 1e-10,
            f"Got {mag}, expected 5.0"
        )
        results.record(
            "Phase extraction",
            abs(phase - math.atan2(4, 3)) < 1e-10,
            f"Got {phase}, expected {math.atan2(4, 3)}"
        )
    except Exception as e:
        results.record("Magnitude/phase", False, str(e))
    
    # Test complex exponential decay
    try:
        decay = engine.complex_exponential_decay(
            t=1.0,
            magnitude_rate=0.01,
            phase_rate=0.001
        )
        results.record(
            "Complex exponential decay",
            abs(decay) > 0 and abs(decay) < 1,
            f"Got {decay}"
        )
    except Exception as e:
        results.record("Complex exponential decay", False, str(e))
    
    # Test complex drift model
    try:
        G0 = 1e-6 + 0j
        G_drifted = engine.complex_drift_model(
            t=2.0,
            G0=G0,
            nu_real=0.01,
            nu_imag=0.001
        )
        results.record(
            "Complex drift model",
            abs(G_drifted) > 0,
            f"Got {G_drifted}"
        )
    except Exception as e:
        results.record("Complex drift model", False, str(e))
    
    return results


def test_device_parameters():
    """Test device parameters."""
    print("\n2. Testing Device Parameters")
    print("-" * 50)
    
    results = TestResults()
    
    # Test RRAM parameters
    try:
        params = DeviceParameters(
            device_type=DeviceType.RRAM,
            resistance_range=(10e3, 100e6),
            write_speed_ns=50,
            write_energy_pJ=0.5,
            endurance_cycles=1e12,
            drift_exponent=0.008
        )
        
        results.record(
            "RRAM parameters created",
            params.device_type == DeviceType.RRAM,
            f"Device type: {params.device_type}"
        )
    except Exception as e:
        results.record("RRAM parameters", False, str(e))
    
    # Test impedance characterization
    try:
        Z = params.characterize_impedance(frequency=1000)
        results.record(
            "Impedance characterization",
            isinstance(Z, complex),
            f"Got {Z}"
        )
    except Exception as e:
        results.record("Impedance characterization", False, str(e))
    
    # Test different device types
    for device_type in [DeviceType.PCM, DeviceType.FEFET, DeviceType.PHOTONIC]:
        try:
            params = DeviceParameters(device_type=device_type)
            results.record(
                f"{device_type.value} parameters",
                params.device_type == device_type,
                f"Device type: {params.device_type}"
            )
        except Exception as e:
            results.record(f"{device_type.value} parameters", False, str(e))
    
    return results


def test_analog_cell():
    """Test analog cell."""
    print("\n3. Testing Analog Cell")
    print("-" * 50)
    
    results = TestResults()
    
    # Test cell creation
    try:
        cell = AnalogCell(
            cell_id=0,
            device_type=DeviceType.RRAM
        )
        results.record(
            "Cell creation",
            cell.cell_id == 0 and cell.device_type == DeviceType.RRAM,
            f"Cell ID: {cell.cell_id}"
        )
    except Exception as e:
        results.record("Cell creation", False, str(e))
    
    # Test impedance measurement
    try:
        cell = AnalogCell(cell_id=0, device_type=DeviceType.RRAM)
        Z = cell.get_impedance(frequency=1000)
        results.record(
            "Impedance measurement",
            isinstance(Z, complex),
            f"Got {Z}"
        )
    except Exception as e:
        results.record("Impedance measurement", False, str(e))
    
    # Test complex programming
    try:
        cell = AnalogCell(cell_id=0, device_type=DeviceType.RRAM)
        target = 1e-6 + 0j
        result = cell.program_complex(
            target=target,
            voltage=1.0,
            pulse_width=50e-9
        )
        results.record(
            "Complex programming",
            result['success'] == True,
            f"Result: {result}"
        )
    except Exception as e:
        results.record("Complex programming", False, str(e))
    
    # Test drift measurement
    try:
        cell = AnalogCell(cell_id=0, device_type=DeviceType.RRAM)
        G_drifted = cell.measure_drift(time_elapsed=100.0)
        results.record(
            "Drift measurement",
            isinstance(G_drifted, complex),
            f"Got {G_drifted}"
        )
    except Exception as e:
        results.record("Drift measurement", False, str(e))
    
    return results


def test_hardware_abstraction():
    """Test universal hardware abstraction layer."""
    print("\n4. Testing Universal HAL")
    print("-" * 50)
    
    results = TestResults()
    
    # Test RRAM HAL initialization
    try:
        hal = RRAM_HAL()
        success = hal.initialize({'num_cells': 16})
        results.record(
            "RRAM HAL initialization",
            success == True,
            f"Success: {success}"
        )
    except Exception as e:
        results.record("RRAM HAL initialization", False, str(e))
    
    # Test device type
    try:
        hal = RRAM_HAL()
        device_type = hal.get_device_type()
        results.record(
            "Device type",
            device_type == DeviceType.RRAM,
            f"Device type: {device_type}"
        )
    except Exception as e:
        results.record("Device type", False, str(e))
    
    # Test conductance read/write
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 8})
        
        # Write
        target = 1e-6 + 0j
        success = hal.write_conductance(cell_id=0, target=target)
        results.record(
            "Conductance write",
            success == True,
            f"Success: {success}"
        )
        
        # Read
        G = hal.read_conductance(cell_id=0)
        results.record(
            "Conductance read",
            isinstance(G, complex),
            f"Got {G}"
        )
    except Exception as e:
        results.record("Conductance read/write", False, str(e))
    
    # Test impedance measurement
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 8})
        
        Z = hal.get_impedance(cell_id=0, frequency=1000)
        results.record(
            "Impedance measurement",
            isinstance(Z, complex),
            f"Got {Z}"
        )
    except Exception as e:
        results.record("Impedance measurement", False, str(e))
    
    # Test status
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 8})
        
        status = hal.get_status()
        results.record(
            "Status",
            'num_cells' in status and status['num_cells'] == 8,
            f"Status: {status}"
        )
    except Exception as e:
        results.record("Status", False, str(e))
    
    return results


def test_self_adaptive_calibration():
    """Test self-adaptive calibration engine."""
    print("\n5. Testing Self-Adaptive Calibration")
    print("-" * 50)
    
    results = TestResults()
    
    # Test calibrator creation
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        calibrator = SelfAdaptiveCalibrator(hal)
        results.record(
            "Calibrator creation",
            calibrator.hal == hal,
            f"Calibrator created"
        )
    except Exception as e:
        results.record("Calibrator creation", False, str(e))
    
    # Test auto-calibration
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        calibrator = SelfAdaptiveCalibrator(hal)
        cal_results = calibrator.auto_calibrate(num_cells=8, num_frequencies=3)
        
        results.record(
            "Auto-calibration",
            cal_results['cells_calibrated'] == 8,
            f"Calibrated: {cal_results['cells_calibrated']} cells"
        )
    except Exception as e:
        results.record("Auto-calibration", False, str(e))
    
    # Test calibration correction
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        calibrator = SelfAdaptiveCalibrator(hal)
        calibrator.auto_calibrate(num_cells=8)
        
        target = 1e-6 + 0j
        corrected = calibrator.get_calibration_correction(cell_id=0, target=target)
        
        results.record(
            "Calibration correction",
            isinstance(corrected, complex),
            f"Got {corrected}"
        )
    except Exception as e:
        results.record("Calibration correction", False, str(e))
    
    return results


def test_predictive_drift_compensation():
    """Test predictive drift compensation engine."""
    print("\n6. Testing Predictive Drift Compensation")
    print("-" * 50)
    
    results = TestResults()
    
    # Test compensator creation
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        compensator = PredictiveDriftCompensator(hal)
        results.record(
            "Compensator creation",
            compensator.hal == hal,
            f"Compensator created"
        )
    except Exception as e:
        results.record("Compensator creation", False, str(e))
    
    # Test tracking initialization
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        compensator = PredictiveDriftCompensator(hal)
        compensator.initialize_tracking(cell_id=0)
        
        results.record(
            "Tracking initialization",
            0 in compensator.drift_trackers,
            f"Trackers: {compensator.drift_trackers.keys()}"
        )
    except Exception as e:
        results.record("Tracking initialization", False, str(e))
    
    # Test drift prediction
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        compensator = PredictiveDriftCompensator(hal)
        compensator.initialize_tracking(cell_id=0)
        
        predicted = compensator.predict_drift(cell_id=0, time_ahead=3600)
        
        results.record(
            "Drift prediction",
            isinstance(predicted, complex),
            f"Got {predicted}"
        )
    except Exception as e:
        results.record("Drift prediction", False, str(e))
    
    # Test drift compensation
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        compensator = PredictiveDriftCompensator(hal)
        compensator.initialize_tracking(cell_id=0)
        
        target = 1e-6 + 0j
        compensated = compensator.compensate_drift(
            cell_id=0,
            target=target,
            current_time=0.0,
            next_access_time=3600.0
        )
        
        results.record(
            "Drift compensation",
            isinstance(compensated, complex),
            f"Got {compensated}"
        )
    except Exception as e:
        results.record("Drift compensation", False, str(e))
    
    return results


def test_kalman_tracker():
    """Test complex Kalman tracker."""
    print("\n7. Testing Complex Kalman Tracker")
    print("-" * 50)
    
    results = TestResults()
    
    # Test tracker creation
    try:
        tracker = ComplexKalmanTracker(cell_id=0)
        results.record(
            "Tracker creation",
            tracker.cell_id == 0,
            f"Tracker created"
        )
    except Exception as e:
        results.record("Tracker creation", False, str(e))
    
    # Test update
    try:
        tracker = ComplexKalmanTracker(cell_id=0)
        tracker.update(measured_G=1e-6 + 0j, timestamp=0.0)
        tracker.update(measured_G=1.1e-6 + 0.01j, timestamp=1.0)
        
        results.record(
            "Tracker update",
            tracker.initialized == True,
            f"Initialized: {tracker.initialized}"
        )
    except Exception as e:
        results.record("Tracker update", False, str(e))
    
    # Test prediction
    try:
        tracker = ComplexKalmanTracker(cell_id=0)
        tracker.update(measured_G=1e-6 + 0j, timestamp=0.0)
        tracker.update(measured_G=1.1e-6 + 0.01j, timestamp=1.0)
        
        predicted = tracker.predict(time_ahead=10.0)
        
        results.record(
            "Tracker prediction",
            isinstance(predicted, complex),
            f"Got {predicted}"
        )
    except Exception as e:
        results.record("Tracker prediction", False, str(e))
    
    # Test confidence
    try:
        tracker = ComplexKalmanTracker(cell_id=0)
        tracker.update(measured_G=1e-6 + 0j, timestamp=0.0)
        
        confidence = tracker.get_confidence()
        
        results.record(
            "Tracker confidence",
            0 <= confidence <= 1,
            f"Got {confidence}"
        )
    except Exception as e:
        results.record("Tracker confidence", False, str(e))
    
    return results


def test_energy_optimizer():
    """Test energy optimization engine."""
    print("\n8. Testing Energy Optimizer")
    print("-" * 50)
    
    results = TestResults()
    
    # Test optimizer creation
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        optimizer = EnergyOptimizer(hal)
        results.record(
            "Optimizer creation",
            optimizer.hal == hal,
            f"Optimizer created"
        )
    except Exception as e:
        results.record("Optimizer creation", False, str(e))
    
    # Test energy profiling
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        optimizer = EnergyOptimizer(hal)
        profile = optimizer.profile_energy(cell_id=0, num_tests=5)
        
        results.record(
            "Energy profiling",
            'energies' in profile and len(profile['energies']) == 5,
            f"Profile: {profile.keys()}"
        )
    except Exception as e:
        results.record("Energy profiling", False, str(e))
    
    # Test pulse sequence optimization
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        optimizer = EnergyOptimizer(hal)
        targets = [1e-6 + 0j, 2e-6 + 0j, 3e-6 + 0j]
        
        pulse_seq = optimizer.optimize_pulse_sequence(
            cell_id=0,
            targets=targets,
            energy_budget=1e-12
        )
        
        results.record(
            "Pulse sequence optimization",
            len(pulse_seq) > 0,
            f"Got {len(pulse_seq)} pulses"
        )
    except Exception as e:
        results.record("Pulse sequence optimization", False, str(e))
    
    # Test energy statistics
    try:
        hal = RRAM_HAL()
        hal.initialize({'num_cells': 16})
        
        optimizer = EnergyOptimizer(hal)
        optimizer.profile_energy(cell_id=0)
        
        # Run an optimization to generate statistics
        targets = [1e-6 + 0j]
        optimizer.optimize_pulse_sequence(
            cell_id=0,
            targets=targets,
            energy_budget=1e-12
        )
        
        stats = optimizer.get_energy_statistics()
        
        results.record(
            "Energy statistics",
            'total_optimizations' in stats and stats['total_optimizations'] > 0,
            f"Stats: {stats}"
        )
    except Exception as e:
        results.record("Energy statistics", False, str(e))
    
    return results


def test_developer_api():
    """Test developer-friendly API."""
    print("\n9. Testing Developer API")
    print("-" * 50)
    
    results = TestResults()
    
    # Test ACR initialization
    try:
        acr = ACR()
        results.record(
            "ACR initialization",
            acr.connected == False and acr.calibrated == False,
            f"Connected: {acr.connected}"
        )
    except Exception as e:
        results.record("ACR initialization", False, str(e))
    
    # Test connection
    try:
        acr = ACR()
        success = acr.connect('rram', {'num_cells': 16})
        
        results.record(
            "ACR connection",
            success == True and acr.connected == True,
            f"Success: {success}"
        )
    except Exception as e:
        results.record("ACR connection", False, str(e))
    
    # Test calibration
    try:
        acr = ACR()
        acr.connect('rram', {'num_cells': 16})
        
        cal_results = acr.calibrate(num_cells=8)
        
        results.record(
            "ACR calibration",
            cal_results['cells_calibrated'] == 8 and acr.calibrated == True,
            f"Calibrated: {cal_results['cells_calibrated']}"
        )
    except Exception as e:
        results.record("ACR calibration", False, str(e))
    
    # Test programming
    try:
        acr = ACR()
        acr.connect('rram', {'num_cells': 16})
        
        target = 1e-6 + 0j
        success = acr.program(cell_id=0, value=target)
        
        results.record(
            "ACR programming",
            success == True,
            f"Success: {success}"
        )
    except Exception as e:
        results.record("ACR programming", False, str(e))
    
    # Test reading
    try:
        acr = ACR()
        acr.connect('rram', {'num_cells': 16})
        
        acr.program(cell_id=0, value=1e-6 + 0j)
        value = acr.read(cell_id=0)
        
        results.record(
            "ACR reading",
            isinstance(value, complex),
            f"Got {value}"
        )
    except Exception as e:
        results.record("ACR reading", False, str(e))
    
    # Test drift prediction
    try:
        acr = ACR()
        acr.connect('rram', {'num_cells': 16})
        
        predicted = acr.predict_drift(cell_id=0, time_ahead=3600)
        
        results.record(
            "ACR drift prediction",
            isinstance(predicted, complex),
            f"Got {predicted}"
        )
    except Exception as e:
        results.record("ACR drift prediction", False, str(e))
    
    # Test impedance measurement
    try:
        acr = ACR()
        acr.connect('rram', {'num_cells': 16})
        
        Z = acr.get_complex_impedance(cell_id=0, frequency=1000)
        
        results.record(
            "ACR impedance measurement",
            isinstance(Z, complex),
            f"Got {Z}"
        )
    except Exception as e:
        results.record("ACR impedance measurement", False, str(e))
    
    # Test Fourier analysis
    try:
        acr = ACR()
        
        signal = np.sin(2 * math.pi * 100 * np.linspace(0, 0.01, 64))
        spectrum = acr.fourier_analyze(signal)
        
        results.record(
            "ACR Fourier analysis",
            isinstance(spectrum, np.ndarray) and len(spectrum) == 64,
            f"Got spectrum of length {len(spectrum)}"
        )
    except Exception as e:
        results.record("ACR Fourier analysis", False, str(e))
    
    # Test status
    try:
        acr = ACR()
        acr.connect('rram', {'num_cells': 16})
        
        status = acr.get_status()
        
        results.record(
            "ACR status",
            'connected' in status and 'calibrated' in status,
            f"Status: {status}"
        )
    except Exception as e:
        results.record("ACR status", False, str(e))
    
    return results


def main():
    """Run all tests."""
    print("=" * 70)
    print("ACR REVOLUTION: COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    all_results = []
    
    # Run all test suites
    all_results.append(test_complex_computation())
    all_results.append(test_device_parameters())
    all_results.append(test_analog_cell())
    all_results.append(test_hardware_abstraction())
    all_results.append(test_self_adaptive_calibration())
    all_results.append(test_predictive_drift_compensation())
    all_results.append(test_kalman_tracker())
    all_results.append(test_energy_optimizer())
    all_results.append(test_developer_api())
    
    # Calculate totals
    total_tests = sum(r.total for r in all_results)
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    
    # Print summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Success rate: {total_passed/total_tests*100:.1f}%")
    
    if total_failed > 0:
        print("\nFailed tests:")
        for result in all_results:
            for name, error in result.errors:
                print(f"  - {name}: {error}")
    
    print("=" * 70)
    
    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
