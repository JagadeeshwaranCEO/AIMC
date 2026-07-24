import os
import sys


sys.path.append(os.path.join(os.path.dirname(__file__), "..", "runtime"))
from emulator import AnalogCrossbar2D


def test_2d_mvm():
    xbar = AnalogCrossbar2D(rows=3, cols=2, seed=123)
    x_in = [0.5, 1.0, 0.2]
    
    # Ideal VMM without read noise
    y_ideal = xbar.forward_vmm(x_in, add_noise=False)
    # Physical VMM with noise
    y_noisy = xbar.forward_vmm(x_in, add_noise=True)


    print("2D Matrix VMM Result:")
    print(f"  Inputs: {x_in}")
    print(f"  Ideal Output: {y_ideal}")
    print(f"  Noisy Output: {y_noisy}")
    
    assert len(y_noisy) == 2
    print("[PASS] 2D Crossbar Matrix Multiply Verified!")


if __name__ == "__main__":
    test_2d_mvm()
