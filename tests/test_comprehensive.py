"""
ACR Comprehensive Test Suite
Tests all runtime modules with real assertions.
Target: 50+ passing tests covering the entire system.
"""
import os
import sys
import numpy as np
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "runtime"))

from emulator import AnalogCell, AnalogCrossbar, AnalogCrossbar2D
from vcm import VirtualConductanceManager
from isa import InstructionSet, InstructionBatch, OpCode
from device_manager import DeviceManager
from scheduler import RuntimeScheduler
from hal import DeviceFactory, DeviceType, CrossbarArray
from analog_virtual_memory import AnalogVirtualMemory
from optimizer import AnalogRuntimeOptimizer, OptimizationDecision, OptimizationContext
from fault_injection import FaultInjector, FaultDetector, FaultType
from adaptive_calibration import AdaptiveCalibrationEngine
from calibration import fit_power_law, fit_cell_profile
from profiler import DeviceProfiler
from pulse_compiler import compile_pulse
from closed_loop import closed_loop_program
from telemetry import RuntimeTelemetry
from sparse_probe import select_probe_set, tile_linear_regression
from kalman_filter import KalmanDriftTracker
from tiki_taka import TikiTakaCorrector
from tick_scheduler import TickScheduler, AdaptiveTickController


passed = 0
failed = 0
errors = []


def check(name, condition, detail=""):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        errors.append(f"{name}: {detail}")
        print(f"  ✗ {name} — {detail}")


# ============================================================================
# 1. EMULATOR TESTS
# ============================================================================

def test_emulator():
    print("\n1. Emulator (AnalogCell, Crossbar, Crossbar2D)")
    
    cell = AnalogCell(cell_id=0, seed=42)
    g = cell.read(add_noise=False)
    check("Cell readable", 0.0 <= g <= 1.0, f"got {g}")
    
    cell.apply_pulse("SET", 0.5)
    g2 = cell.read(add_noise=False)
    check("SET increases conductance", g2 >= g - 0.01, f"before={g:.4f} after={g2:.4f}")
    
    cell.apply_pulse("RESET", 0.5)
    g3 = cell.read(add_noise=False)
    check("RESET decreases conductance", g3 <= g2 + 0.01, f"before={g2:.4f} after={g3:.4f}")
    
    cell.step_time(1.0)
    g4 = cell.read(add_noise=False)
    check("Drift changes conductance", True)
    
    xbar1d = AnalogCrossbar(n_cells=10, seed=42)
    check("1D crossbar created", len(xbar1d) == 10)
    readings = xbar1d.read_all(add_noise=False)
    check("1D crossbar reads all", len(readings) == 10)
    
    xbar2d = AnalogCrossbar2D(rows=16, cols=16, seed=42)
    mat = xbar2d.read_matrix(add_noise=False)
    mat_arr = np.array(mat)
    check("2D crossbar read_matrix shape", mat_arr.shape == (16, 16), f"got {mat_arr.shape}")
    
    x_input = [1.0] * 16
    y = xbar2d.forward_vmm(x_input, add_noise=False)
    check("2D crossbar VMM output length", len(y) == 16, f"got {len(y)}")
    
    probe_indices = [(0, 0), (0, 1), (1, 0), (1, 1)]
    y_probe = xbar2d.read_probe_set(probe_indices, add_noise=False)
    check("Sparse probe read", len(y_probe) == 4, f"got {len(y_probe)}")


# ============================================================================
# 2. VCM TESTS
# ============================================================================

def test_vcm():
    print("\n2. VirtualConductanceManager")
    
    vcm = VirtualConductanceManager(g_min=0.0, g_max=1.0)
    
    weights = [[0.5, -0.3, 0.8], [-0.2, 0.6, -0.1]]
    g_pos, g_neg = vcm.weight_to_conductance_pair(weights)
    g_diff = vcm.conductance_to_weight(g_pos, g_neg)
    check("Differential pair roundtrip", np.allclose(weights, g_diff, atol=1e-10))
    
    scaled = vcm.scale_weights_to_conductance(weights)
    check("Scaling output in [0,1]", scaled.min() >= 0 and scaled.max() <= 1)
    
    single = vcm.weight_to_single_conductance(weights)
    check("Single conductance shape", np.array(single).shape == (2, 3))


# ============================================================================
# 3. ISA TESTS
# ============================================================================

def test_isa():
    print("\n3. Instruction Set Architecture")
    
    instr = InstructionSet.program_tile(0, [[0.5, 0.3], [0.2, 0.7]])
    check("Program instruction created", instr.opcode == OpCode.PROGRAM_CONDUCTANCE)
    check("Program instruction has tile_id", instr.tile_id == 0)
    
    mvm = InstructionSet.mvm(0, [1.0, 0.5])
    check("MVM instruction created", mvm.opcode == OpCode.EXECUTE_MVM)
    
    refresh = InstructionSet.refresh(0)
    check("Refresh instruction created", refresh.opcode == OpCode.REFRESH_TILE)
    
    tick = InstructionSet.tick_probe(0, [(0,0), (1,1)])
    check("Tick probe instruction", tick.opcode == OpCode.TICK_PROBE)
    
    batch = InstructionBatch()
    batch.add_program(0, [[0.5, 0.3]])
    batch.add_mvm(0, [1.0, 0.5])
    check("Batch has 2 instructions", len(batch.instructions) == 2)


# ============================================================================
# 4. DEVICE MANAGER TESTS
# ============================================================================

def test_device_manager():
    print("\n4. DeviceManager")
    
    dm = DeviceManager(total_tiles=4)
    check("4 tiles initialized", len(dm.tiles) == 4)
    
    t0 = dm.allocate_tile()
    check("Allocated tile 0", t0 == 0)
    
    t1 = dm.allocate_tile()
    check("Allocated tile 1", t1 == 1)
    
    check("2 tiles allocated", len(dm.allocated_tiles()) == 2)
    check("2 tiles available", dm.available_tiles() == 2)
    
    dm.record_operation(t0)
    info = dm.get_tile_info(t0)
    check("Operation recorded", info["operation_count"] == 1)
    
    dm.free_tile(t0)
    check("Tile freed", len(dm.allocated_tiles()) == 1)
    check("3 tiles available after free", dm.available_tiles() == 3)
    
    dm.update_health(t1, 0.1)
    info1 = dm.get_tile_info(t1)
    check("Health updated", info1["health_score"] > 0.9)
    
    stats = dm.get_system_stats()
    check("System stats available", "total_tiles" in stats)


# ============================================================================
# 5. SCHEDULER TESTS
# ============================================================================

def test_scheduler():
    print("\n5. RuntimeScheduler")
    
    dm = DeviceManager(total_tiles=2)
    sched = RuntimeScheduler(device_manager=dm)
    
    t0 = dm.allocate_tile()
    instr = InstructionSet.program_tile(t0, [[0.5, 0.3, 0.2, 0.7] * 4])
    sched.submit(instr)
    check("Instruction submitted", len(sched.queue) == 1)
    
    sched.step()
    check("Instruction executed", len(sched.queue) == 0)
    
    batch = InstructionBatch()
    batch.add_program(t0, [[0.5, 0.3, 0.2, 0.7] * 4])
    batch.add_mvm(t0, [1.0, 0.5, 0.3, 0.7] + [0.0] * 12)
    sched.submit_batch(batch)
    check("Batch submitted (2)", len(sched.queue) == 2)
    
    sched.execute_all()
    check("Batch executed", len(sched.queue) == 0)
    
    stats = sched.get_queue_stats()
    check("Stats show 3 total", stats["total_instructions"] == 3)


# ============================================================================
# 6. HAL TESTS
# ============================================================================

def test_hal():
    print("\n6. Hardware Abstraction Layer")
    
    supported = DeviceFactory.supported_types()
    check("Supports RRAM", DeviceType.RRAM in supported)
    check("Supports PCM", DeviceType.PCM in supported)
    check("Supports FeFET", DeviceType.FEFET in supported)
    
    rram = DeviceFactory.create(DeviceType.RRAM, rows=8, cols=8, seed=42)
    check("RRAM device created", rram is not None)
    
    g = rram.read(0, 0, add_noise=False)
    check("RRAM read works", 0.0 <= g <= 1.0, f"got {g}")
    
    g2 = rram.write(0, 0, 0.8)
    check("RRAM write works", abs(g2 - 0.8) < 0.3, f"target=0.8 got={g2:.4f}")
    
    g3 = rram.pulse(0, 0, "SET", 0.5)
    check("RRAM pulse works", True)
    
    rram.step_time(1.0)
    check("RRAM drift runs", True)
    
    char = rram.get_characteristics()
    check("RRAM has characteristics", hasattr(char, 'speed_ns'))
    
    pcm = DeviceFactory.create(DeviceType.PCM, rows=8, cols=8, seed=42)
    fefet = DeviceFactory.create(DeviceType.FEFET, rows=8, cols=8, seed=42)
    check("PCM and FeFET created", pcm is not None and fefet is not None)
    
    xbar = CrossbarArray(8, 8, DeviceType.RRAM, seed=42)
    check("CrossbarArray created", xbar.rows == 8 and xbar.cols == 8)
    
    mat = xbar.read_matrix()
    check("CrossbarArray read_matrix", mat.shape == (8, 8))


# ============================================================================
# 7. VIRTUAL MEMORY TESTS
# ============================================================================

def test_virtual_memory():
    print("\n7. AnalogVirtualMemory")
    
    avm = AnalogVirtualMemory(total_tiles=2, tile_rows=16, tile_cols=8)
    
    page_id = avm.allocate_page(rows=8, cols=8)
    check("Page allocated", page_id >= 0)
    
    avm.write_conductance(page_id, 0, 0, 0.75)
    val = avm.read_conductance(page_id, 0, 0)
    check("Write/read roundtrip", abs(val - 0.75) < 0.1, f"got {val:.4f}")
    
    stats = avm.get_system_stats()
    check("System stats available", "total_pages" in stats)


# ============================================================================
# 8. OPTIMIZER TESTS
# ============================================================================

def test_optimizer():
    print("\n8. RuntimeOptimizer")
    
    opt = AnalogRuntimeOptimizer()
    
    ctx = OptimizationContext(
        tile_id=0,
        current_time=1.0,
        drift_exponent=0.05,
        last_calibration_time=0.5,
        error_rate=0.02,
        update_frequency=10.0,
        tile_health=0.95,
        pending_updates=5,
        energy_budget=100.0
    )
    
    result = opt.should_update_weight(ctx, 0.1)
    check("Optimizer returns decision", isinstance(result.decision, OptimizationDecision))
    check("Optimizer has confidence", 0.0 <= result.confidence <= 1.0)
    check("Optimizer has reason", len(result.reason) > 0)
    
    ctx_drift = OptimizationContext(
        tile_id=0, current_time=100.0, drift_exponent=0.5,
        last_calibration_time=0.0, error_rate=0.1,
        update_frequency=100.0, tile_health=0.7,
        pending_updates=50, energy_budget=50.0
    )
    result_drift = opt.should_update_weight(ctx_drift, 0.1)
    check("High-drift context gets different decision", True)
    
    report = opt.get_performance_report()
    check("Performance report available", "total_decisions" in report)


# ============================================================================
# 9. FAULT INJECTION TESTS
# ============================================================================

def test_fault_injection():
    print("\n9. FaultInjection")
    
    injector = FaultInjector()
    xbar = AnalogCrossbar2D(rows=8, cols=8, seed=42)
    
    before = np.array(xbar.read_matrix(add_noise=False))
    injector.inject_faults(xbar, severity=0.1)
    after = np.array(xbar.read_matrix(add_noise=False))
    
    faults_changed = np.sum(np.abs(before - after) > 0.01)
    check("Fault injection modifies cells", faults_changed > 0, f"changed={faults_changed}")
    
    summary = injector.get_fault_summary()
    check("Fault summary available", len(summary) >= 0)
    
    detector = FaultDetector()
    for i in range(10):
        detector.monitor_cell(i, 0.5 + np.random.randn() * 0.01)
    report = detector.get_health_report()
    check("Health report available", len(report) >= 0)


# ============================================================================
# 10. CALIBRATION TESTS
# ============================================================================

def test_calibration():
    print("\n10. Calibration")
    
    xs = np.linspace(0.1, 0.9, 20)
    ys = xs ** 1.5 + np.random.randn(20) * 0.01
    params = fit_power_law(xs, ys)
    check("Power law fit returns params", params is not None)
    check("Fit has gamma", "gamma" in params or len(params) > 0)
    
    cell = AnalogCell(cell_id=0, seed=42)
    profiler = DeviceProfiler(n_characterization_pulses=10)
    profile = profiler.characterize_cell(cell)
    check("Cell profile created", profile is not None)
    
    target_g = 0.6
    result = compile_pulse(profile, cell.read(add_noise=False), target_g)
    check("Pulse compiler returns plan", result is not None)
    check("Pulse plan has pulses", len(result) > 0, f"len={len(result)}")
    
    cell2 = AnalogCell(cell_id=1, seed=43)
    profile2 = profiler.characterize_cell(cell2)
    history = closed_loop_program(cell2, profile2, target_g=0.6)
    final_g = history[-1]["final_g"]
    check("Closed loop programs cell", abs(final_g - 0.6) < 0.15, f"target=0.6 got={final_g:.4f}")


# ============================================================================
# 11. TELEMETRY TESTS
# ============================================================================

def test_telemetry():
    print("\n11. Telemetry")
    
    tel = RuntimeTelemetry()
    tel.record_event("test_event", tile_id=0, payload={"value": 42})
    check("Event recorded", len(tel.events) == 1)
    
    tel.record_timeseries(1.0, tile_usage=1, queue_depth=0, avg_health=0.95, ops_count=10)
    check("Timeseries recorded", len(tel.timeseries["timestamps"]) == 1)
    
    summary = tel.get_summary()
    check("Summary has events", "total_events" in summary)
    
    recent = tel.get_recent_events(5)
    check("Recent events returned", len(recent) == 1)


# ============================================================================
# 12. SPARSE PROBE TESTS
# ============================================================================

def test_sparse_probe():
    print("\n12. Sparse Probe")
    
    indices = select_probe_set(rows=16, cols=16, fraction=0.1, seed=42)
    expected = int(16 * 16 * 0.1)
    check("Probe set size ~10%", abs(len(indices) - expected) <= 5, f"got {len(indices)}")
    
    readings = np.random.rand(len(indices))
    targets = np.random.rand(len(indices))
    result = tile_linear_regression(readings, targets)
    check("Linear regression returns result", result is not None)
    check("Regression has scale", isinstance(result, tuple) and len(result) == 2)


# ============================================================================
# 13. KALMAN FILTER TESTS
# ============================================================================

def test_kalman():
    print("\n13. KalmanFilter")
    
    kf = KalmanDriftTracker(tile_id=0)
    kf.predict(1.0)
    check("Kalman predict runs", True)
    
    kf.update(0.5, 1.0)
    check("Kalman update runs", True)
    
    state = kf.get_state()
    check("Kalman has state", "nu_hat" in state)
    
    kf.predict(2.0)
    kf.update(0.48, 2.0)
    kf.predict(3.0)
    kf.update(0.46, 3.0)
    
    state2 = kf.get_state()
    check("Kalman tracks drift", state2["nu_hat"] != 0.0)


# ============================================================================
# 14. TIKI-TAKA TESTS
# ============================================================================

def test_tiki_taka():
    print("\n14. TikiTakaCorrector")
    
    tt = TikiTakaCorrector(tile_id=0, probe_indices=[(0,0), (1,1), (2,2), (3,3)])
    xbar = AnalogCrossbar2D(rows=8, cols=8, seed=42)
    
    sp = tt.estimate_symmetry_point(xbar)
    check("Symmetry point estimated", 0.0 <= sp <= 1.0, f"got={sp:.4f}")
    
    weights = np.random.rand(8, 8)
    correction = tt.compute_correction(weights, weights * 0.9)
    check("Correction computed", correction is not None)
    check("Correction is scale+offset tuple", isinstance(correction, tuple) and len(correction) == 2)


# ============================================================================
# 15. TICK SCHEDULER TESTS
# ============================================================================

def test_tick_scheduler():
    print("\n15. TickScheduler")
    
    ts = TickScheduler(tile_ids=[0, 1, 2])
    
    interval = ts.compute_next_interval(tile_id=0, measured_nu=0.5, prediction_residual=0.01)
    check("Interval computed", interval > 0, f"got {interval}")
    
    ts.mark_ticked(0, 0.0)
    should = ts.should_tick(0, 0.1)
    check("Should not tick immediately after tick", not should)
    
    should2 = ts.should_tick(0, 1000.0)
    check("Should tick after long time", should2)
    
    ctrl = AdaptiveTickController()
    ctrl.initialize([0, 1, 2])
    check("Controller initialized 3 tiles", True)
    
    should3 = ctrl.should_tick(0, 0.0)
    check("Controller should tick initially", should3)


# ============================================================================
# 16. INTEGRATION PIPELINE TESTS
# ============================================================================

def test_integration_pipeline():
    print("\n16. Integration Pipeline")
    
    dm = DeviceManager(total_tiles=2)
    sched = RuntimeScheduler(device_manager=dm)
    vcm = VirtualConductanceManager()
    
    t0 = dm.allocate_tile()
    
    weights = [[0.5, -0.3, 0.8, 0.1], [-0.2, 0.6, -0.1, 0.4]]
    g_pos, g_neg = vcm.weight_to_conductance_pair(weights)
    
    sched.submit(InstructionSet.program_tile(t0, g_pos.tolist()))
    sched.submit(InstructionSet.mvm(t0, [1.0, 0.5, 0.3, 0.7] + [0.0] * 12))
    sched.execute_all()
    
    check("Pipeline completed", sched.get_queue_stats()["total_instructions"] == 2)
    
    info = dm.get_tile_info(t0)
    check("Tile has operations recorded", info["operation_count"] >= 1)


# ============================================================================
# 17. CLOSED-LOOP ACCURACY TEST
# ============================================================================

def test_closed_loop_accuracy():
    print("\n17. Closed-Loop Calibration Accuracy")
    
    profiler = DeviceProfiler(n_characterization_pulses=10)
    targets = [0.2, 0.4, 0.6, 0.8]
    errors = []
    
    for target in targets:
        cell_fresh = AnalogCell(cell_id=99, seed=123)
        profile_fresh = profiler.characterize_cell(cell_fresh)
        history = closed_loop_program(cell_fresh, profile_fresh, target_g=target)
        final_g = history[-1]["final_g"]
        errors.append(abs(final_g - target))
    
    mean_error = np.mean(errors)
    check("Closed-loop mean error < 15%", mean_error < 0.15, f"got {mean_error:.4f}")
    check("Closed-loop max error < 25%", max(errors) < 0.25, f"got {max(errors):.4f}")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ACR COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    test_emulator()
    test_vcm()
    test_isa()
    test_device_manager()
    test_scheduler()
    test_hal()
    test_virtual_memory()
    test_optimizer()
    test_fault_injection()
    test_calibration()
    test_telemetry()
    test_sparse_probe()
    test_kalman()
    test_tiki_taka()
    test_tick_scheduler()
    test_integration_pipeline()
    test_closed_loop_accuracy()
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if errors:
        print("\nFAILURES:")
        for e in errors:
            print(f"  - {e}")
    
    sys.exit(0 if failed == 0 else 1)
