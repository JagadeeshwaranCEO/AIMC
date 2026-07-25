"""
ACR Revolution v2: Holy Trinity Test Suite

Tests for the three revolutionary equations:
1. Langevin Equation (Thermodynamic Computing)
2. Neural ODEs (Continuous Depth Computing)
3. Crossbar Arrays (O(1) Matrix Multiplication)

Author: Jagadeeshwaran E (Team Lead)
Date: July 2026
"""

import sys
import os
import math
import numpy as np

# Add runtime to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runtime'))

from acr_holy_trinity import (
    ThermodynamicComputer,
    NeuralODE,
    CrossbarArray,
    ThermodynamicNeuralODE,
    ACR_Thermodynamic
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


def test_thermodynamic_computer():
    """Test Langevin equation thermodynamic computing."""
    print("\n1. Testing Thermodynamic Computer (Langevin Equation)")
    print("-" * 50)
    
    results = TestResults()
    
    # Test initialization
    try:
        thermo = ThermodynamicComputer(temperature=300.0)
        results.record(
            "Thermodynamic computer initialization",
            thermo.temperature == 300.0 and thermo.D > 0,
            f"T={thermo.temperature}, D={thermo.D:.2e}"
        )
    except Exception as e:
        results.record("Thermodynamic computer initialization", False, str(e))
    
    # Test Langevin step
    try:
        thermo = ThermodynamicComputer(temperature=300.0)
        x_new = thermo.langevin_step(x=0.0, dt=1e-9)
        results.record(
            "Langevin step",
            isinstance(x_new, float),
            f"New position: {x_new}"
        )
    except Exception as e:
        results.record("Langevin step", False, str(e))
    
    # Test distribution sampling
    try:
        thermo = ThermodynamicComputer(temperature=300.0, potential="harmonic")
        samples = thermo.sample_distribution(num_samples=1000)
        results.record(
            "Distribution sampling",
            len(samples) == 1000 and np.std(samples) > 0,
            f"Mean: {np.mean(samples):.4f}, Std: {np.std(samples):.4f}"
        )
    except Exception as e:
        results.record("Distribution sampling", False, str(e))
    
    # Test Boltzmann average
    try:
        thermo = ThermodynamicComputer(temperature=300.0, potential="harmonic")
        avg = thermo.compute_boltzmann_average(lambda x: x**2, num_samples=1000)
        results.record(
            "Boltzmann average",
            avg > 0,
            f"<x^2> = {avg:.4f}"
        )
    except Exception as e:
        results.record("Boltzmann average", False, str(e))
    
    # Test Boltzmann machine simulation
    try:
        thermo = ThermodynamicComputer(temperature=300.0)
        samples = thermo.simulate_boltzmann_machine(num_neurons=4, num_samples=100)
        results.record(
            "Boltzmann machine simulation",
            samples.shape == (100, 4),
            f"Shape: {samples.shape}"
        )
    except Exception as e:
        results.record("Boltzmann machine simulation", False, str(e))
    
    return results


def test_neural_ode():
    """Test Neural Ordinary Differential Equations."""
    print("\n2. Testing Neural ODE (Continuous Depth)")
    print("-" * 50)
    
    results = TestResults()
    
    # Test initialization
    try:
        node = NeuralODE(input_dim=2, hidden_dim=4, output_dim=2)
        results.record(
            "Neural ODE initialization",
            node.input_dim == 2 and node.hidden_dim == 4,
            f"Dimensions: {node.input_dim}→{node.hidden_dim}→{node.output_dim}"
        )
    except Exception as e:
        results.record("Neural ODE initialization", False, str(e))
    
    # Test forward dynamics
    try:
        node = NeuralODE(input_dim=2, hidden_dim=4, output_dim=2)
        h = np.array([1.0, 0.0, 0.0, 0.0])  # hidden_dim = 4
        t = 0.0
        dhdt = node.forward_dynamics(h, t)
        results.record(
            "Forward dynamics",
            isinstance(dhdt, np.ndarray) and len(dhdt) == 4,
            f"dh/dt shape: {dhdt.shape}"
        )
    except Exception as e:
        results.record("Forward dynamics", False, str(e))
    
    # Test Euler solver
    try:
        node = NeuralODE(input_dim=2, hidden_dim=4, output_dim=2, method="euler")
        h0 = np.array([1.0, 0.0, 0.0, 0.0])  # hidden_dim = 4
        t_span = np.linspace(0, 1, 100)
        trajectory = node.solve(h0, t_span)
        results.record(
            "Euler solver",
            trajectory.shape == (100, 4),
            f"Trajectory shape: {trajectory.shape}"
        )
    except Exception as e:
        results.record("Euler solver", False, str(e))
    
    # Test RK4 solver
    try:
        node = NeuralODE(input_dim=2, hidden_dim=4, output_dim=2, method="rk4")
        h0 = np.array([1.0, 0.0, 0.0, 0.0])  # hidden_dim = 4
        t_span = np.linspace(0, 1, 100)
        trajectory = node.solve(h0, t_span)
        results.record(
            "RK4 solver",
            trajectory.shape == (100, 4),
            f"Trajectory shape: {trajectory.shape}"
        )
    except Exception as e:
        results.record("RK4 solver", False, str(e))
    
    # Test forward pass
    try:
        node = NeuralODE(input_dim=2, hidden_dim=4, output_dim=2)
        x = np.array([1.0, 0.0])
        y = node.forward(x)
        results.record(
            "Forward pass",
            isinstance(y, np.ndarray) and len(y) == 2,
            f"Output shape: {y.shape}"
        )
    except Exception as e:
        results.record("Forward pass", False, str(e))
    
    # Test Jacobian computation
    try:
        node = NeuralODE(input_dim=2, hidden_dim=4, output_dim=2)
        h = np.array([1.0, 0.0, 0.0, 0.0])  # hidden_dim = 4
        t = 0.0
        J = node.compute_jacobian(h, t)
        results.record(
            "Jacobian computation",
            J.shape == (4, 4),
            f"Jacobian shape: {J.shape}"
        )
    except Exception as e:
        results.record("Jacobian computation", False, str(e))
    
    return results


def test_crossbar_array():
    """Test Crossbar Array O(1) matrix multiplication."""
    print("\n3. Testing Crossbar Array (O(1) Matrix Multiplication)")
    print("-" * 50)
    
    results = TestResults()
    
    # Test initialization
    try:
        crossbar = CrossbarArray(rows=4, cols=4)
        results.record(
            "Crossbar array initialization",
            crossbar.rows == 4 and crossbar.cols == 4,
            f"Size: {crossbar.rows}x{crossbar.cols}"
        )
    except Exception as e:
        results.record("Crossbar array initialization", False, str(e))
    
    # Test matrix programming
    try:
        crossbar = CrossbarArray(rows=4, cols=4)
        W = np.array([[1, 0, 0, 0],
                      [0, 1, 0, 0],
                      [0, 0, 1, 0],
                      [0, 0, 0, 1]], dtype=float)
        crossbar.program_matrix(W)
        results.record(
            "Matrix programming",
            np.min(crossbar.G) > 0 and np.max(crossbar.G) > 0,
            f"Conductance range: [{np.min(crossbar.G):.2e}, {np.max(crossbar.G):.2e}]"
        )
    except Exception as e:
        results.record("Matrix programming", False, str(e))
    
    # Test matrix-vector multiplication
    try:
        crossbar = CrossbarArray(rows=4, cols=4)
        W = np.array([[1, 0, 0, 0],
                      [0, 1, 0, 0],
                      [0, 0, 1, 0],
                      [0, 0, 0, 1]], dtype=float)
        crossbar.program_matrix(W)
        
        V = np.array([1.0, 2.0, 3.0, 4.0])
        I = crossbar.compute(V)
        
        # Check that the result is proportional to expected
        # (conductance scaling means exact values differ)
        expected = np.dot(W, V)
        proportional = np.allclose(I / I[0], expected / expected[0], rtol=1e-2)
        
        results.record(
            "Matrix-vector multiplication",
            proportional,
            f"Got {I}, expected {expected}"
        )
    except Exception as e:
        results.record("Matrix-vector multiplication", False, str(e))
    
    # Test computation with noise
    try:
        crossbar = CrossbarArray(rows=4, cols=4)
        crossbar.program_matrix(np.eye(4))
        
        V = np.array([1.0, 2.0, 3.0, 4.0])
        I_noisy = crossbar.compute_with_noise(V, noise_level=0.1)
        
        results.record(
            "Computation with noise",
            isinstance(I_noisy, np.ndarray) and np.std(I_noisy) > 0,
            f"Noisy output: {I_noisy}"
        )
    except Exception as e:
        results.record("Computation with noise", False, str(e))
    
    # Test energy consumption
    try:
        crossbar = CrossbarArray(rows=4, cols=4)
        crossbar.program_matrix(np.eye(4))
        
        V = np.array([1.0, 2.0, 3.0, 4.0])
        energy = crossbar.get_energy_consumption(V)
        
        results.record(
            "Energy consumption",
            energy > 0,
            f"Energy: {energy:.2e} J"
        )
    except Exception as e:
        results.record("Energy consumption", False, str(e))
    
    # Test theoretical speedup
    try:
        crossbar = CrossbarArray(rows=4, cols=4)
        speedup = crossbar.get_theoretical_speedup(digital_flops=1e9)
        
        results.record(
            "Theoretical speedup",
            speedup == 16,  # 4x4 = 16
            f"Speedup: {speedup}x"
        )
    except Exception as e:
        results.record("Theoretical speedup", False, str(e))
    
    # Test training simulation
    try:
        crossbar = CrossbarArray(rows=2, cols=2)
        X = np.random.randn(10, 2)
        Y = np.random.randn(10, 2)
        
        W_trained = crossbar.simulate_training(X, Y, epochs=10, learning_rate=0.01)
        
        results.record(
            "Training simulation",
            W_trained.shape == (2, 2),
            f"Trained weights shape: {W_trained.shape}"
        )
    except Exception as e:
        results.record("Training simulation", False, str(e))
    
    return results


def test_thermodynamic_neural_ode():
    """Test integrated Thermodynamic Neural ODE system."""
    print("\n4. Testing Thermodynamic Neural ODE Integration")
    print("-" * 50)
    
    results = TestResults()
    
    # Test initialization
    try:
        system = ThermodynamicNeuralODE(
            input_dim=2,
            hidden_dim=4,
            output_dim=2,
            temperature=300.0
        )
        results.record(
            "Thermodynamic Neural ODE initialization",
            system.input_dim == 2 and system.hidden_dim == 4,
            f"Dimensions: {system.input_dim}→{system.hidden_dim}→{system.output_dim}"
        )
    except Exception as e:
        results.record("Thermodynamic Neural ODE initialization", False, str(e))
    
    # Test forward pass
    try:
        system = ThermodynamicNeuralODE(
            input_dim=2,
            hidden_dim=4,
            output_dim=2,
            temperature=300.0
        )
        x = np.array([1.0, 0.0])
        y = system.forward(x, use_thermodynamic=False)
        
        results.record(
            "Forward pass",
            isinstance(y, np.ndarray) and len(y) == 2,
            f"Output: {y}"
        )
    except Exception as e:
        results.record("Forward pass", False, str(e))
    
    # Test posterior sampling
    try:
        system = ThermodynamicNeuralODE(
            input_dim=2,
            hidden_dim=4,
            output_dim=2,
            temperature=300.0
        )
        x = np.array([1.0, 0.0])
        samples = system.sample_from_posterior(x, num_samples=50)
        
        results.record(
            "Posterior sampling",
            samples.shape == (50, 2),
            f"Samples shape: {samples.shape}"
        )
    except Exception as e:
        results.record("Posterior sampling", False, str(e))
    
    # Test uncertainty computation
    try:
        system = ThermodynamicNeuralODE(
            input_dim=2,
            hidden_dim=4,
            output_dim=2,
            temperature=300.0
        )
        x = np.array([1.0, 0.0])
        uncertainty = system.compute_uncertainty(x, num_samples=50)
        
        results.record(
            "Uncertainty computation",
            'mean' in uncertainty and 'variance' in uncertainty,
            f"Uncertainty keys: {uncertainty.keys()}"
        )
    except Exception as e:
        results.record("Uncertainty computation", False, str(e))
    
    # Test training
    try:
        system = ThermodynamicNeuralODE(
            input_dim=2,
            hidden_dim=4,
            output_dim=2,
            temperature=300.0
        )
        X_train = np.random.randn(20, 2)
        Y_train = np.random.randn(20, 2)
        
        losses = system.train(X_train, Y_train, epochs=20, learning_rate=0.01)
        
        results.record(
            "Training",
            len(losses) == 20 and all(isinstance(l, float) for l in losses),
            f"Initial loss: {losses[0]:.4f}, Final loss: {losses[-1]:.4f}"
        )
    except Exception as e:
        results.record("Training", False, str(e))
    
    return results


def test_acr_thermodynamic():
    """Test ACR Thermodynamic integration."""
    print("\n5. Testing ACR Thermodynamic Integration")
    print("-" * 50)
    
    results = TestResults()
    
    # Test initialization
    try:
        acr = ACR_Thermodynamic(device_type="rram", temperature=300.0)
        results.record(
            "ACR Thermodynamic initialization",
            acr.device_type == "rram" and acr.temperature == 300.0,
            f"Device: {acr.device_type}, T={acr.temperature}K"
        )
    except Exception as e:
        results.record("ACR Thermodynamic initialization", False, str(e))
    
    # Test system initialization
    try:
        acr = ACR_Thermodynamic(device_type="rram")
        acr.initialize(input_dim=2, hidden_dim=4, output_dim=2)
        
        results.record(
            "System initialization",
            acr.initialized == True,
            f"Initialized: {acr.initialized}"
        )
    except Exception as e:
        results.record("System initialization", False, str(e))
    
    # Test forward computation
    try:
        acr = ACR_Thermodynamic(device_type="rram")
        acr.initialize(input_dim=2, hidden_dim=4, output_dim=2)
        
        x = np.array([1.0, 0.0])
        y = acr.compute(x, use_thermodynamic=False)
        
        results.record(
            "Forward computation",
            isinstance(y, np.ndarray) and len(y) == 2,
            f"Output: {y}"
        )
    except Exception as e:
        results.record("Forward computation", False, str(e))
    
    # Test posterior sampling
    try:
        acr = ACR_Thermodynamic(device_type="rram")
        acr.initialize(input_dim=2, hidden_dim=4, output_dim=2)
        
        x = np.array([1.0, 0.0])
        samples = acr.sample_from_posterior(x, num_samples=50)
        
        results.record(
            "Posterior sampling",
            samples.shape == (50, 2),
            f"Samples shape: {samples.shape}"
        )
    except Exception as e:
        results.record("Posterior sampling", False, str(e))
    
    # Test uncertainty computation
    try:
        acr = ACR_Thermodynamic(device_type="rram")
        acr.initialize(input_dim=2, hidden_dim=4, output_dim=2)
        
        x = np.array([1.0, 0.0])
        uncertainty = acr.compute_uncertainty(x, num_samples=50)
        
        results.record(
            "Uncertainty computation",
            'mean' in uncertainty and 'variance' in uncertainty,
            f"Uncertainty keys: {uncertainty.keys()}"
        )
    except Exception as e:
        results.record("Uncertainty computation", False, str(e))
    
    # Test training
    try:
        acr = ACR_Thermodynamic(device_type="rram")
        acr.initialize(input_dim=2, hidden_dim=4, output_dim=2)
        
        X_train = np.random.randn(20, 2)
        Y_train = np.random.randn(20, 2)
        
        losses = acr.train(X_train, Y_train, epochs=20, learning_rate=0.01)
        
        results.record(
            "Training",
            len(losses) == 20 and all(isinstance(l, float) for l in losses),
            f"Initial loss: {losses[0]:.4f}, Final loss: {losses[-1]:.4f}"
        )
    except Exception as e:
        results.record("Training", False, str(e))
    
    return results


def main():
    """Run all tests."""
    print("=" * 70)
    print("ACR REVOLUTION v2: HOLY TRINITY TEST SUITE")
    print("=" * 70)
    print("\nTesting the three revolutionary equations:")
    print("1. Langevin Equation (Thermodynamic Computing)")
    print("2. Neural ODEs (Continuous Depth Computing)")
    print("3. Crossbar Arrays (O(1) Matrix Multiplication)")
    print("=" * 70)
    
    all_results = []
    
    # Run all test suites
    all_results.append(test_thermodynamic_computer())
    all_results.append(test_neural_ode())
    all_results.append(test_crossbar_array())
    all_results.append(test_thermodynamic_neural_ode())
    all_results.append(test_acr_thermodynamic())
    
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
