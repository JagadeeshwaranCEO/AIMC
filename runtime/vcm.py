"""
ACR Virtual Conductance Manager (VCM)
Maps neural network weights to physical device conductances.

Analog memory cells only support non-negative conductance values (G ∈ [G_min, G_max]).
The VCM maps unbounded floating-point neural network weights W ∈ ℝ into
differential cell pairs (G⁺ - G⁻) or scaled conductance targets.
"""
import numpy as np


class VirtualConductanceManager:
    def __init__(self, g_min=0.0, g_max=1.0):
        self.g_min = g_min
        self.g_max = g_max

    def weight_to_conductance_pair(self, weight_matrix):
        """
        Differential pair mapping: W = G_pos - G_neg
        Maps real weights into two positive conductance matrices.
        
        Args:
            weight_matrix: 2D array-like of weights (can be negative)
            
        Returns:
            Tuple of (g_pos, g_neg) as numpy arrays
        """
        w_array = np.array(weight_matrix)
        g_pos = np.clip(np.maximum(0, w_array), self.g_min, self.g_max)
        g_neg = np.clip(np.maximum(0, -w_array), self.g_min, self.g_max)
        return g_pos, g_neg

    def conductance_to_weight(self, g_pos, g_neg):
        """Reconstructs effective weight matrix from differential conductances."""
        return np.array(g_pos) - np.array(g_neg)

    def weight_to_single_conductance(self, weight_matrix):
        """
        Single-ended mapping for weights already in [0, 1] range.
        Assumes input weights are pre-scaled to conductance range.
        """
        w_array = np.array(weight_matrix)
        return np.clip(w_array, self.g_min, self.g_max)

    def scale_weights_to_conductance(self, weight_matrix, g_range=None):
        """
        Linearly scales arbitrary weight matrix to fit within conductance range.
        Useful for mapping weights with arbitrary magnitudes.
        """
        if g_range is None:
            g_range = (self.g_min, self.g_max)
        
        w_array = np.array(weight_matrix)
        w_min, w_max = w_array.min(), w_array.max()
        
        if w_max - w_min < 1e-10:
            return np.full_like(w_array, (g_range[0] + g_range[1]) / 2)
        
        scaled = (w_array - w_min) / (w_max - w_min)
        return scaled * (g_range[1] - g_range[0]) + g_range[0]

    def get_differential_conductance(self, weight_matrix):
        """
        Returns full differential representation: (g_pos, g_neg, g_diff)
        where g_diff = g_pos - g_neg is the effective weight.
        """
        g_pos, g_neg = self.weight_to_conductance_pair(weight_matrix)
        g_diff = self.conductance_to_weight(g_pos, g_neg)
        return g_pos, g_neg, g_diff


if __name__ == "__main__":
    vcm = VirtualConductanceManager(g_min=0.0, g_max=1.0)
    
    test_weights = [
        [0.5, -0.3, 0.8],
        [-0.2, 0.6, -0.1],
        [0.4, -0.7, 0.9]
    ]
    
    print("Original weights:")
    print(np.array(test_weights))
    
    g_pos, g_neg = vcm.weight_to_conductance_pair(test_weights)
    print("\nPositive conductances (G⁺):")
    print(g_pos)
    print("\nNegative conductances (G⁻):")
    print(g_neg)
    
    g_diff = vcm.conductance_to_weight(g_pos, g_neg)
    print("\nEffective weights (G⁺ - G⁻):")
    print(g_diff)
    
    print("\nVCM functional!")
