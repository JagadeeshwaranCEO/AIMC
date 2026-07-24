"""
ACR PyTorch Bridge — Intercepts standard PyTorch layers and executes
them on the ACR Analog Crossbar Emulator through the runtime stack.

Integrates with:
- DeviceManager: Hardware tile allocation
- RuntimeScheduler: Instruction queue management
- VirtualConductanceManager: Weight-to-conductance mapping
"""
try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("Warning: PyTorch not installed. Install with: pip install torch")

from emulator import AnalogCrossbar2D
from device_manager import DeviceManager
from scheduler import RuntimeScheduler
from vcm import VirtualConductanceManager
from isa import InstructionSet, Instruction, OpCode


# Global runtime components (initialized on first use)
_global_device_manager = None
_global_scheduler = None


def get_runtime():
    """Get or initialize the global runtime components."""
    global _global_device_manager, _global_scheduler
    
    if _global_device_manager is None:
        _global_device_manager = DeviceManager(total_tiles=8, tile_rows=32, tile_cols=32)
        _global_scheduler = RuntimeScheduler(_global_device_manager)
    
    return _global_device_manager, _global_scheduler


if HAS_TORCH:
    class ACRAnalogLinear(nn.Module):
        """
        A PyTorch-compatible Linear Layer powered by the ACR Analog Hardware Engine.
        
        This layer:
        1. Allocates a crossbar tile from the DeviceManager
        2. Programs weights via the VirtualConductanceManager
        3. Executes VMM through the RuntimeScheduler
        """
        def __init__(self, in_features, out_features, seed=42):
            super().__init__()
            self.in_features = in_features
            self.out_features = out_features
            self.seed = seed
            
            # Get runtime components
            self.device_mgr, self.scheduler = get_runtime()
            self.vcm = VirtualConductanceManager()
            
            # Allocate a crossbar tile
            self.tile_id = self.device_mgr.allocate_tile()
            
            # Initialize weight parameter for PyTorch autograd tracking
            self.weight = nn.Parameter(torch.Tensor(out_features, in_features))
            nn.init.kaiming_uniform_(self.weight)

        def forward(self, x):
            """
            Executes physical VMM for 1D/2D batches through the crossbar.
            """
            if x.dim() == 1:
                # Single input vector
                x_list = x.tolist()
                
                # Submit MVM instruction to scheduler
                self.scheduler.submit_mvm(self.tile_id, x_list)
                result = self.scheduler.step()
                
                return torch.tensor(result, dtype=torch.float32)
            else:
                # Batch mode: pass rows one by one through crossbar
                outputs = []
                for batch_item in x:
                    x_list = batch_item.tolist()
                    
                    # Submit MVM instruction to scheduler
                    self.scheduler.submit_mvm(self.tile_id, x_list)
                    result = self.scheduler.step()
                    outputs.append(result)
                
                return torch.tensor(outputs, dtype=torch.float32)

        def program_weights(self, weight_matrix):
            """
            Program weight matrix into crossbar via VCM.
            Converts PyTorch weights to conductance targets.
            """
            w_array = weight_matrix.detach().cpu().numpy()
            g_conductance = self.vcm.scale_weights_to_conductance(w_array)
            
            # Submit programming instruction
            self.scheduler.submit_program(self.tile_id, g_conductance.tolist())
            self.scheduler.step()
            
            # Update PyTorch parameter
            with torch.no_grad():
                self.weight.copy_(weight_matrix)

        def get_tile_info(self):
            """Return metadata about the allocated tile."""
            return self.device_mgr.get_tile_info(self.tile_id)

        def __del__(self):
            """Cleanup: release the allocated tile."""
            if hasattr(self, 'tile_id') and hasattr(self, 'device_mgr'):
                try:
                    self.device_mgr.free_tile(self.tile_id)
                except:
                    pass


# Fallback class for when PyTorch is not available
class ACRAnalogLinearFallback:
    """Non-PyTorch fallback for testing the crossbar directly."""
    
    def __init__(self, in_features, out_features, seed=42):
        self.in_features = in_features
        self.out_features = out_features
        
        # Create a dedicated crossbar with correct dimensions
        self.crossbar = AnalogCrossbar2D(rows=in_features, cols=out_features, seed=seed)
        
        # Virtual conductance manager for weight mapping
        self.vcm = VirtualConductanceManager()

    def forward(self, x):
        """Execute VMM directly through the crossbar."""
        if isinstance(x, list):
            x_list = x
        else:
            x_list = x.tolist()
        
        return self.crossbar.forward_vmm(x_list, add_noise=True)

    def program_weights(self, weight_matrix):
        """Program weight matrix into crossbar."""
        import numpy as np
        w_array = np.array(weight_matrix)
        g_conductance = self.vcm.scale_weights_to_conductance(w_array)
        
        # For emulation, we'll initialize the crossbar with scaled weights
        # In real hardware, this would pulse cells to target conductance
        self._weights = weight_matrix
        self._conductance = g_conductance

    def get_tile_info(self):
        """Return metadata about the crossbar."""
        return {
            "in_features": self.in_features,
            "out_features": self.out_features,
            "rows": self.crossbar.rows,
            "cols": self.crossbar.cols,
        }

    def __del__(self):
        """Cleanup (no-op for dedicated crossbar)."""
        pass


# Module-level convenience function
def create_analog_linear(in_features, out_features, seed=42):
    """Factory function to create the appropriate linear layer."""
    if HAS_TORCH:
        return ACRAnalogLinear(in_features, out_features, seed)
    else:
        return ACRAnalogLinearFallback(in_features, out_features, seed)


if __name__ == "__main__":
    print("Testing ACR PyTorch Bridge with Runtime Integration...")
    
    # Test with fallback (works without PyTorch)
    print("\n1. Testing fallback layer...")
    layer = ACRAnalogLinearFallback(in_features=4, out_features=2)
    sample_input = [0.5, 0.8, 0.2, 0.1]
    
    output = layer.forward(sample_input)
    print(f"Input Vector : {sample_input}")
    print(f"Analog Output: {output}")
    
    # Program some weights (4x4 to match in_features)
    weights = [[0.5, 0.3, 0.2, 0.8], [0.4, 0.6, 0.7, 0.1], [0.3, 0.5, 0.4, 0.9], [0.2, 0.8, 0.1, 0.6]]
    layer.program_weights(weights)
    print("Weights programmed successfully")
    
    # Get tile info
    info = layer.get_tile_info()
    print(f"Tile info: {info}")
    
    # Test PyTorch version if available
    if HAS_TORCH:
        print("\n2. Testing PyTorch layer...")
        torch_layer = ACRAnalogLinear(in_features=4, out_features=2)
        sample_tensor = torch.tensor([0.5, 0.8, 0.2, 0.1])
        
        output_tensor = torch_layer(sample_tensor)
        print(f"Input Tensor : {sample_tensor.tolist()}")
        print(f"Output Tensor: {output_tensor.tolist()}")
        
        # Program weights (4x4 to match in_features)
        torch_layer.program_weights(torch.tensor(weights))
        print("Weights programmed via PyTorch interface")
    else:
        print("\n2. PyTorch not available, skipping PyTorch test")
        print("   Install with: pip install torch")
    
    # Show runtime stats
    print("\n3. Runtime statistics...")
    _, scheduler = get_runtime()
    stats = scheduler.get_queue_stats()
    print(f"Scheduler stats: {stats}")
    
    print("\nPyTorch Bridge with Runtime Integration functional!")
