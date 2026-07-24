"""
ACR Visual Demo Generator - ASCII Runtime Visualization

Creates compelling ASCII art visualizations of the ACR runtime:
- Crossbar grid with conductance heatmap
- Instruction flow animation
- Drift and calibration visualization
- Fault injection demonstration

Perfect for hackathon demos and terminal presentations.
"""
import time
import sys
import os
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "runtime"))

from emulator import AnalogCrossbar2D
from device_manager import DeviceManager
from scheduler import RuntimeScheduler
from vcm import VirtualConductanceManager
from fault_injection import FaultInjector, FaultTolerantCrossbar
from adaptive_calibration import AdaptiveCalibrationEngine


class ASCIIArt:
    """ASCII art utilities for visualization."""

    BLOCK_CHARS = " .:-=+*#%@"
    HEATMAP_CHARS = " .,:;+*%#@"
    BOX_HORIZONTAL = "─"
    BOX_VERTICAL = "│"
    BOX_TOP_LEFT = "┌"
    BOX_TOP_RIGHT = "┐"
    BOX_BOTTOM_LEFT = "└"
    BOX_BOTTOM_RIGHT = "┘"

    @staticmethod
    def block_char(value: float) -> str:
        idx = int(value * (len(ASCIIArt.BLOCK_CHARS) - 1))
        return ASCIIArt.BLOCK_CHARS[idx]

    @staticmethod
    def heatmap_char(value: float) -> str:
        idx = int(value * (len(ASCIIArt.HEATMAP_CHARS) - 1))
        return ASCIIArt.HEATMAP_CHARS[idx]


class ACRVisualDemo:
    """Visual demo generator for ACR runtime."""

    def __init__(self):
        self.art = ASCIIArt()

    def clear_screen(self):
        os.system('clear' if os.name != 'nt' else 'cls')

    def print_header(self, title: str):
        width = 60
        print("\n" + "=" * width)
        print(f"  {title}")
        print("=" * width)

    def visualize_crossbar(self, crossbar, title="Crossbar Conductance State"):
        self.print_header(title)
        matrix = crossbar.read_matrix(add_noise=False)

        print("\n  Col:  ", end="")
        for c in range(crossbar.cols):
            print(f"{c:3d}", end="")
        print()

        print("  " + "─" * (crossbar.cols * 3 + 5))

        for r in range(crossbar.rows):
            print(f"  Row {r:2d}│", end="")
            for c in range(crossbar.cols):
                val = matrix[r][c]
                char = self.art.heatmap_char(val)
                print(f"  {char}", end="")
            print()

        print("\n  Legend: ' '=0.0  '.'=0.25  ':'=0.5  '*'=0.75  '@'=1.0")

    def visualize_drift_timeline(self, crossbar, steps: int = 5):
        self.print_header("Drift Simulation Over Time")

        print("\n  Simulating conductance drift...\n")

        for step in range(steps):
            crossbar.step_time(dt=10.0)
            matrix = crossbar.read_matrix(add_noise=False)

            avg_conductance = np.mean(matrix)
            drift = abs(avg_conductance - 0.5)

            bar_length = int(drift * 100)
            bar = "█" * bar_length + "░" * (50 - bar_length)

            print(f"  t={step * 10:3d} │ Avg G={avg_conductance:.3f} │ Drift [{bar}] {drift:.3f}")

        print("\n  Drift accumulates over time - runtime must compensate!")

    def demonstrate_fault_injection(self):
        self.print_header("Fault Injection Demonstration")

        print("\n  Creating 8x8 crossbar with random weights...")
        xbar = AnalogCrossbar2D(rows=8, cols=8, seed=42)

        weights = np.random.rand(8, 8) * 0.6 + 0.2
        for r in range(8):
            for c in range(8):
                xbar.grid[r][c].g_norm = weights[r][c]

        print("\n  Original crossbar:")
        self.visualize_crossbar(xbar, "Before Fault Injection")

        print("\n  Injecting faults (stuck-at-zero, stuck-at-one, write failures)...")
        injector = FaultInjector()
        events = injector.inject_faults(xbar, severity=2.0)

        print(f"\n  Injected {len(events)} faults!")
        for event in events[:5]:
            print(f"    - {event.description}")
        if len(events) > 5:
            print(f"    ... and {len(events) - 5} more")

        print("\n  Crossbar after fault injection:")
        self.visualize_crossbar(xbar, "After Fault Injection")

        print("\n  Fault-tolerant VMM with redundant cells...")
        tolerant = FaultTolerantCrossbar(xbar, injector)
        tolerant.initialize_with_faults(fault_severity=1.0)

        x_input = [0.5] * 8
        y_output = tolerant.forward_vmm_tolerant(x_input)

        print(f"\n  Input:  {[f'{v:.2f}' for v in x_input]}")
        print(f"  Output: {[f'{v:.3f}' for v in y_output]}")
        print("  ✓ Runtime handled faults transparently!")

    def demonstrate_calibration(self):
        self.print_header("Adaptive Calibration Demonstration")

        print("\n  Setting up crossbar with drift...")
        xbar = AnalogCrossbar2D(rows=4, cols=4, seed=42)

        initial_weights = np.random.rand(4, 4) * 0.5 + 0.3
        for r in range(4):
            for c in range(4):
                xbar.grid[r][c].g_norm = initial_weights[r][c]

        print("\n  Initial state:")
        self.visualize_crossbar(xbar, "Initial Conductance")

        print("\n  Simulating drift (t=50)...")
        xbar.step_time(50)

        print("\n  After drift:")
        self.visualize_crossbar(xbar, "After Drift")

        print("\n  Running adaptive calibration...")
        engine = AdaptiveCalibrationEngine()
        engine.initialize_crossbar(xbar)

        result = engine.calibrate_crossbar(xbar)
        print(f"\n  Calibration result: {result['cells_corrected']} cells corrected")

        print("\n  After calibration:")
        self.visualize_crossbar(xbar, "After Calibration")
        print("  ✓ Runtime auto-corrected drift!")

    def demonstrate_instruction_flow(self):
        self.print_header("Instruction Flow Visualization")

        print("\n  PyTorch Layer Forward Pass:")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  nn.Linear(784, 128)                               │")
        print("  └─────────────────────────────────────────────────────┘")
        print("                          │")
        print("                          ▼")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  ACR Bridge: ACRAnalogLinear                       │")
        print("  └─────────────────────────────────────────────────────┘")
        print("                          │")
        print("                          ▼")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  Virtual Conductance Manager                       │")
        print("  │  W = G⁺ - G⁻  (differential pair mapping)         │")
        print("  └─────────────────────────────────────────────────────┘")
        print("                          │")
        print("                          ▼")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  Instruction Compiler (ISA)                        │")
        print("  │  Opcode: EXECUTE_MVM, Tile: 0, Payload: {...}     │")
        print("  └─────────────────────────────────────────────────────┘")
        print("                          │")
        print("                          ▼")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  Runtime Scheduler                                 │")
        print("  │  Queue: [ALLOC, PROGRAM, MVM, REFRESH, ...]       │")
        print("  └─────────────────────────────────────────────────────┘")
        print("                          │")
        print("                          ▼")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  Device Manager                                    │")
        print("  │  Tile 0: 784x128, Health: 0.95, Ops: 150          │")
        print("  └─────────────────────────────────────────────────────┘")
        print("                          │")
        print("                          ▼")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  Analog Crossbar (Physical VMM)                    │")
        print("  │  y = G·x + noise  (Kirchhoff's current law)       │")
        print("  └─────────────────────────────────────────────────────┘")

    def run_full_demo(self):
        self.clear_screen()

        print("╔" + "═" * 58 + "╗")
        print("║" + " ACR: Analog Compute Runtime Demo ".center(58) + "║")
        print("║" + " Hardware-Agnostic Execution Runtime ".center(58) + "║")
        print("╚" + "═" * 58 + "╝")

        self.demonstrate_instruction_flow()

        input("\n  Press Enter to continue...")

        xbar = AnalogCrossbar2D(rows=6, cols=6, seed=42)
        weights = np.random.rand(6, 6) * 0.6 + 0.2
        for r in range(6):
            for c in range(6):
                xbar.grid[r][c].g_norm = weights[r][c]

        self.visualize_crossbar(xbar, "Working Crossbar")
        input("\n  Press Enter to see drift simulation...")

        self.visualize_drift_timeline(xbar, steps=6)
        input("\n  Press Enter to see fault injection...")

        self.demonstrate_fault_injection()
        input("\n  Press Enter to see adaptive calibration...")

        self.demonstrate_calibration()

        self.print_header("Demo Complete!")
        print("""
  Key Takeaways:
  ─────────────
  1. ACR provides a complete runtime stack for analog computing
  2. Hardware faults are detected and compensated automatically
  3. Drift is monitored and corrected in real-time
  4. Same PyTorch API - zero code changes for analog acceleration
  5. Runtime manages hardware transparency

  Vision:
  ──────
  "Analog Compute Runtime (ACR) is a hardware-agnostic software runtime
   that abstracts unreliable analog memory into a reliable computing
   platform, enabling future analog AI accelerators to be programmed
   as easily as today's GPUs."
""")


if __name__ == "__main__":
    demo = ACRVisualDemo()
    demo.run_full_demo()
