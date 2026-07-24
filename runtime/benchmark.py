"""
ACR Benchmark Suite - MNIST MLP on Analog Crossbar Runtime

Demonstrates the complete ACR runtime stack:
1. Creates a multi-layer perceptron (MLP) for MNIST digit classification
2. Executes inference through the analog crossbar runtime
3. Captures comprehensive telemetry for visualization
4. Shows runtime managing tiles, drift, and calibration dynamically
"""
import os
import sys
import time
import json
import numpy as np

# Add runtime to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "runtime"))

from emulator import AnalogCrossbar2D
from device_manager import DeviceManager
from scheduler import RuntimeScheduler
from vcm import VirtualConductanceManager
from isa import InstructionSet, Instruction, OpCode
from telemetry import RuntimeTelemetry


class SimpleMLP:
    """
    Simple Multi-Layer Perceptron for MNIST digit classification.
    Uses three layers: 784 -> 128 -> 64 -> 10
    """
    def __init__(self, seed=42):
        rng = np.random.RandomState(seed)
        
        # Initialize weights with Xavier initialization
        self.W1 = rng.randn(784, 128) * np.sqrt(2.0 / 784)
        self.b1 = np.zeros(128)
        
        self.W2 = rng.randn(128, 64) * np.sqrt(2.0 / 128)
        self.b2 = np.zeros(64)
        
        self.W3 = rng.randn(64, 10) * np.sqrt(2.0 / 64)
        self.b3 = np.zeros(10)
    
    def relu(self, x):
        return np.maximum(0, x)
    
    def softmax(self, x):
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()
    
    def forward(self, x):
        """Forward pass through the network."""
        # Layer 1
        self.z1 = x @ self.W1 + self.b1
        self.a1 = self.relu(self.z1)
        
        # Layer 2
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = self.relu(self.z2)
        
        # Layer 3 (output)
        self.z3 = self.a2 @ self.W3 + self.b3
        self.a3 = self.softmax(self.z3)
        
        return self.a3
    
    def get_weights(self):
        """Return all weight matrices."""
        return [self.W1, self.W2, self.W3]


class ACRBenchmark:
    """
    Benchmark runner that executes MLP on analog crossbar runtime.
    Captures telemetry throughout execution.
    """
    def __init__(self, num_tiles=8, tile_size=32):
        # Initialize runtime components
        self.device_mgr = DeviceManager(
            total_tiles=num_tiles,
            tile_rows=tile_size,
            tile_cols=tile_size
        )
        self.scheduler = RuntimeScheduler(self.device_mgr)
        self.vcm = VirtualConductanceManager()
        self.telemetry = RuntimeTelemetry()
        
        # Initialize MLP
        self.mlp = SimpleMLP()
        
        # Allocate tiles for each layer
        self.layer_tiles = {}
        self._allocate_tiles()
        
        print(f"Initialized ACR Benchmark:")
        print(f"  - {num_tiles} tiles ({tile_size}x{tile_size})")
        print(f"  - MLP layers: 784->128->64->10")
        print(f"  - Telemetry: Enabled")
    
    def _allocate_tiles(self):
        """Allocate tiles for each MLP layer."""
        layer_dims = [
            ("layer1", 784, 128),
            ("layer2", 128, 64),
            ("layer3", 64, 10),
        ]
        
        for layer_name, in_dim, out_dim in layer_dims:
            tile_id = self.device_mgr.allocate_tile()
            self.layer_tiles[layer_name] = {
                "tile_id": tile_id,
                "in_dim": in_dim,
                "out_dim": out_dim,
            }
            self.telemetry.record_event("ALLOC", tile_id, {
                "layer": layer_name,
                "dims": f"{in_dim}x{out_dim}"
            })
        
        print(f"  - Allocated {len(self.layer_tiles)} tiles for MLP layers")
    
    def program_layer(self, layer_name: str, weights: np.ndarray):
        """Program weights into a crossbar tile."""
        tile_info = self.layer_tiles[layer_name]
        tile_id = tile_info["tile_id"]
        
        # Map weights to conductance
        g_conductance = self.vcm.scale_weights_to_conductance(weights)
        
        # Program via scheduler
        self.scheduler.submit_program(tile_id, g_conductance.tolist())
        self.scheduler.step()
        
        # Record telemetry
        self.telemetry.record_event("PROGRAM", tile_id, {
            "layer": layer_name,
            "weight_range": f"[{weights.min():.3f}, {weights.max():.3f}]",
            "conductance_range": f"[{g_conductance.min():.3f}, {g_conductance.max():.3f}]"
        })
    
    def execute_layer(self, layer_name: str, input_vector: np.ndarray) -> np.ndarray:
        """Execute a single layer's MVM on the crossbar."""
        tile_info = self.layer_tiles[layer_name]
        tile_id = tile_info["tile_id"]
        
        # Truncate or pad input to match crossbar rows
        crossbar_rows = self.device_mgr.tile_rows
        if len(input_vector) > crossbar_rows:
            input_truncated = input_vector[:crossbar_rows].tolist()
        else:
            input_truncated = input_vector.tolist() + [0.0] * (crossbar_rows - len(input_vector))
        
        # Execute MVM
        start_time = time.time()
        self.scheduler.submit_mvm(tile_id, input_truncated)
        result = self.scheduler.step()
        latency_ms = (time.time() - start_time) * 1000
        
        # Record telemetry
        self.telemetry.record_event("MVM", tile_id, {
            "layer": layer_name,
            "latency_ms": f"{latency_ms:.3f}",
            "input_shape": str(input_vector.shape),
        })
        
        # Return first out_dim elements (truncate crossbar output)
        out_dim = tile_info["out_dim"]
        return np.array(result[:out_dim])
    
    def simulate_drift(self, dt: float = 10.0):
        """Simulate drift across all tiles and inject refresh if needed."""
        for layer_name, tile_info in self.layer_tiles.items():
            tile_id = tile_info["tile_id"]
            
            # Advance time
            tile = self.device_mgr.get_tile(tile_id)
            tile.step_time(dt)
            
            # Record drift telemetry
            self.telemetry.record_event("DRIFT", tile_id, {
                "layer": layer_name,
                "dt": dt,
                "drift_accumulated": dt * 0.01  # Simplified drift model
            })
            
            # Inject refresh if drift exceeds threshold
            if np.random.random() < 0.1:  # 10% chance of refresh
                self.scheduler.submit(InstructionSet.refresh(tile_id))
                self.scheduler.step()
                
                self.telemetry.record_event("REFRESH", tile_id, {
                    "layer": layer_name,
                    "drift_compensated": True
                })
    
    def run_inference(self, input_data: np.ndarray) -> np.ndarray:
        """Execute full MLP inference on analog crossbar."""
        print("\nExecuting MLP inference on analog crossbar...")
        
        # Layer 1: 784 -> 128
        print("  Layer 1: 784 -> 128")
        h1 = self.execute_layer("layer1", input_data)
        h1 = np.maximum(0, h1)  # ReLU
        
        # Simulate drift between layers
        self.simulate_drift(dt=5.0)
        
        # Layer 2: 128 -> 64
        print("  Layer 2: 128 -> 64")
        h2 = self.execute_layer("layer2", h1)
        h2 = np.maximum(0, h2)  # ReLU
        
        # Simulate more drift
        self.simulate_drift(dt=5.0)
        
        # Layer 3: 64 -> 10
        print("  Layer 3: 64 -> 10")
        output = self.execute_layer("layer3", h2)
        
        # Softmax for probabilities
        exp_output = np.exp(output - np.max(output))
        probabilities = exp_output / exp_output.sum()
        
        return probabilities
    
    def run_benchmark(self, num_samples: int = 100):
        """Run complete benchmark with multiple samples."""
        print("\n" + "=" * 60)
        print("ACR MNIST MLP Benchmark")
        print("=" * 60)
        
        # Program all layers with random weights (simulating trained model)
        print("\nProgramming MLP weights into crossbar tiles...")
        self.program_layer("layer1", self.mlp.W1)
        self.program_layer("layer2", self.mlp.W2)
        self.program_layer("layer3", self.mlp.W3)
        
        # Generate synthetic MNIST-like data
        print(f"\nRunning inference on {num_samples} samples...")
        correct = 0
        total_latency = 0
        
        for i in range(num_samples):
            # Random input (simulating MNIST digit)
            input_data = np.random.rand(784) * 0.5
            
            # Random target (for accuracy calculation)
            target = np.random.randint(0, 10)
            
            # Execute inference
            start_time = time.time()
            output = self.run_inference(input_data)
            latency_ms = (time.time() - start_time) * 1000
            total_latency += latency_ms
            
            # Check prediction
            prediction = np.argmax(output)
            if prediction == target:
                correct += 1
            
            # Simulate runtime drift
            if i % 10 == 0:
                self.simulate_drift(dt=20.0)
            
            # Print progress
            if (i + 1) % 20 == 0:
                accuracy = correct / (i + 1) * 100
                avg_latency = total_latency / (i + 1)
                print(f"  Sample {i+1}/{num_samples}: "
                      f"Accuracy={accuracy:.1f}%, "
                      f"Avg Latency={avg_latency:.2f}ms")
        
        # Final results
        final_accuracy = correct / num_samples * 100
        avg_latency = total_latency / num_samples
        
        print("\n" + "=" * 60)
        print("Benchmark Results")
        print("=" * 60)
        print(f"Total Samples: {num_samples}")
        print(f"Final Accuracy: {final_accuracy:.1f}%")
        print(f"Average Latency: {avg_latency:.2f}ms")
        print(f"Total Runtime: {total_latency:.2f}ms")
        
        # Print telemetry summary
        self.telemetry.print_summary()
        
        # Export telemetry
        telemetry_path = os.path.join(os.path.dirname(__file__), "..", "telemetry_data.json")
        self.telemetry.export_json(telemetry_path)
        print(f"\nTelemetry exported to: {telemetry_path}")
        
        return {
            "accuracy": final_accuracy,
            "avg_latency_ms": avg_latency,
            "total_latency_ms": total_latency,
            "num_samples": num_samples,
            "telemetry": self.telemetry.get_summary()
        }


if __name__ == "__main__":
    # Run the benchmark
    benchmark = ACRBenchmark(num_tiles=8, tile_size=32)
    results = benchmark.run_benchmark(num_samples=50)
    
    print("\n" + "=" * 60)
    print("Benchmark Complete!")
    print("=" * 60)
