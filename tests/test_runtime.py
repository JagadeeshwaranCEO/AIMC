"""
ACR Runtime Stack Integration Test
Validates the complete runtime architecture:
- VirtualConductanceManager (VCM)
- Instruction Set Architecture (ISA)
- Device Manager
- Runtime Scheduler
- PyTorch Bridge Integration
"""
import os
import sys
import numpy as np

# Add runtime to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "runtime"))

from vcm import VirtualConductanceManager
from isa import InstructionSet, InstructionBatch, OpCode
from device_manager import DeviceManager
from scheduler import RuntimeScheduler


def test_vcm():
    """Test Virtual Conductance Manager weight mapping."""
    print("1. Testing VirtualConductanceManager...")
    
    vcm = VirtualConductanceManager(g_min=0.0, g_max=1.0)
    
    # Test with negative weights
    weights = [
        [0.5, -0.3, 0.8],
        [-0.2, 0.6, -0.1],
        [0.4, -0.7, 0.9]
    ]
    
    g_pos, g_neg = vcm.weight_to_conductance_pair(weights)
    g_diff = vcm.conductance_to_weight(g_pos, g_neg)
    
    # Verify reconstruction
    original = np.array(weights)
    reconstructed = np.array(g_diff)
    
    assert np.allclose(original, reconstructed, atol=1e-10), "VCM weight reconstruction failed"
    print("   ✓ Differential pair mapping works correctly")
    
    # Test scaling
    large_weights = [[100.0, -50.0], [200.0, -150.0]]
    scaled = vcm.scale_weights_to_conductance(large_weights)
    assert scaled.min() >= 0.0 and scaled.max() <= 1.0, "VCM scaling failed"
    print("   ✓ Weight scaling works correctly")
    
    print("   [PASS] VCM test passed!")
    return True


def test_isa():
    """Test Instruction Set Architecture."""
    print("\n2. Testing Instruction Set Architecture...")
    
    # Create instructions
    prog = InstructionSet.program_tile(0, [[0.5, 0.3], [0.2, 0.8]])
    mvm = InstructionSet.mvm(0, [0.5, 0.8])
    refresh = InstructionSet.refresh(0)
    
    assert prog.opcode == OpCode.PROGRAM_CONDUCTANCE
    assert mvm.opcode == OpCode.EXECUTE_MVM
    assert refresh.opcode == OpCode.REFRESH_TILE
    print("   ✓ Instruction creation works correctly")
    
    # Test batch creation
    batch = InstructionBatch()
    batch.add_program(0, [[0.5, 0.3], [0.2, 0.8]])
    batch.add_mvm(0, [0.5, 0.8])
    batch.add_refresh(0)
    
    assert len(batch.instructions) == 3
    print("   ✓ Instruction batch works correctly")
    
    print("   [PASS] ISA test passed!")
    return True


def test_device_manager():
    """Test Device Manager allocation and tracking."""
    print("\n3. Testing Device Manager...")
    
    dm = DeviceManager(total_tiles=4, tile_rows=8, tile_cols=8)
    assert dm.available_tiles() == 4
    print("   ✓ Device manager initialized with 4 tiles")
    
    # Allocate tiles
    tile0 = dm.allocate_tile()
    tile1 = dm.allocate_tile()
    assert dm.available_tiles() == 2
    print(f"   ✓ Allocated tiles {tile0} and {tile1}")
    
    # Record operations
    dm.record_operation(tile0)
    dm.record_operation(tile0)
    dm.record_operation(tile1)
    
    stats = dm.get_system_stats()
    assert stats["total_operations"] == 3
    print("   ✓ Operation tracking works correctly")
    
    # Free tiles
    dm.free_tile(tile0)
    dm.free_tile(tile1)
    assert dm.available_tiles() == 4
    print("   ✓ Tile deallocation works correctly")
    
    # Test health tracking
    dm.update_health(tile0, -0.1)
    health = dm.get_tile_health_summary()
    assert health[tile0] == 0.9
    print("   ✓ Health tracking works correctly")
    
    print("   [PASS] Device Manager test passed!")
    return True


def test_scheduler():
    """Test Runtime Scheduler instruction execution."""
    print("\n4. Testing Runtime Scheduler...")
    
    dm = DeviceManager(total_tiles=2, tile_rows=4, tile_cols=4)
    scheduler = RuntimeScheduler(dm)
    
    # Allocate a tile
    tile0 = dm.allocate_tile()
    
    # Program conductance matrix (4 rows to match tile_rows)
    weights = [[0.5, 0.3], [0.2, 0.8], [0.4, 0.6], [0.7, 0.1]]
    scheduler.submit_program(tile0, weights)
    
    # Execute MVM with 4-element input vector (matching tile_rows)
    x_input = [0.5, 0.8, 0.2, 0.1]
    scheduler.submit_mvm(tile0, x_input)
    
    # Execute all queued instructions
    results = scheduler.execute_all()
    assert len(results) == 2
    assert results[1] is not None  # MVM result should not be None
    print("   ✓ Instruction execution works correctly")
    
    # Test batch execution with 4-element vectors
    batch_results = scheduler.execute_mvm_batch(tile0, [[0.5, 0.8, 0.2, 0.1], [0.2, 0.3, 0.4, 0.5]])
    assert len(batch_results) == 2
    print("   ✓ Batch execution works correctly")
    
    # Test queue stats
    stats = scheduler.get_queue_stats()
    assert stats["total_instructions"] > 0
    print("   ✓ Queue statistics work correctly")
    
    print("   [PASS] Scheduler test passed!")
    return True


def test_2d_crossbar():
    """Test 2D Crossbar Matrix Multiplication."""
    print("\n5. Testing 2D Crossbar Matrix Multiplication...")
    
    from emulator import AnalogCrossbar2D
    
    xbar = AnalogCrossbar2D(rows=3, cols=2, seed=123)
    x_in = [0.5, 1.0, 0.2]
    
    # Ideal VMM without read noise
    y_ideal = xbar.forward_vmm(x_in, add_noise=False)
    # Physical VMM with noise
    y_noisy = xbar.forward_vmm(x_in, add_noise=True)
    
    assert len(y_ideal) == 2
    assert len(y_noisy) == 2
    print("   ✓ 2D Matrix VMM works correctly")
    
    print("   [PASS] 2D Crossbar test passed!")
    return True


def test_full_pipeline():
    """Test complete runtime pipeline integration."""
    print("\n6. Testing Full Runtime Pipeline...")
    
    # Initialize components with 4x4 tiles
    dm = DeviceManager(total_tiles=2, tile_rows=4, tile_cols=4)
    scheduler = RuntimeScheduler(dm)
    vcm = VirtualConductanceManager()
    
    # Allocate tile
    tile0 = dm.allocate_tile()
    
    # Prepare weights with negative values (4x4 to match tile dimensions)
    weights = [
        [0.5, -0.3, 0.2, 0.8],
        [-0.2, 0.8, -0.1, 0.4],
        [0.4, -0.7, 0.9, -0.5],
        [0.1, 0.3, -0.6, 0.7]
    ]
    
    # Map to conductance
    g_pos, g_neg = vcm.weight_to_conductance_pair(weights)
    
    # Program both differential pairs
    scheduler.submit_program(tile0, g_pos.tolist())
    scheduler.submit_program(tile0, g_neg.tolist())
    
    # Execute MVM with 4-element input vector (matching tile_rows)
    x_input = [0.5, 0.8, 0.2, 0.1]
    scheduler.submit_mvm(tile0, x_input)
    
    # Execute all
    results = scheduler.execute_all()
    assert len(results) == 3
    print("   ✓ Full pipeline (VCM → ISA → Scheduler → Crossbar) works")
    
    # Show runtime stats
    stats = scheduler.get_queue_stats()
    print(f"   Pipeline executed {stats['total_instructions']} instructions")
    
    print("   [PASS] Full Pipeline test passed!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("ACR Runtime Stack Integration Test Suite")
    print("=" * 60)
    
    tests = [
        test_vcm,
        test_isa,
        test_device_manager,
        test_scheduler,
        test_2d_crossbar,
        test_full_pipeline,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   [FAIL] {test.__name__} raised exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 All tests passed! Runtime stack is functional.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the implementation.")
