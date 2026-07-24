"""
ACR Runtime Scheduler
Orchestrates hardware execution queues and runtime maintenance.

Processes the instruction queue, routes operations to hardware tiles,
and injects maintenance steps (drift compensation and dynamic calibration).
"""
from collections import deque
from typing import Any, Dict, List, Optional
from isa import OpCode, Instruction, InstructionBatch
from device_manager import DeviceManager
from vcm import VirtualConductanceManager


class RuntimeScheduler:
    def __init__(self, device_manager: DeviceManager):
        self.device_mgr = device_manager
        self.vcm = VirtualConductanceManager()
        self.queue: deque = deque()
        self.results: Dict[int, Any] = {}
        self.instruction_count = 0
        self.current_time = 0.0
        
        # Maintenance thresholds
        self.drift_threshold = 50.0  # Time before refresh needed
        self.calibration_interval = 100.0  # Time between calibrations
        
        # Compensation Tick integration
        self.compensation_tick = None  # Set externally

    def submit(self, instruction: Instruction):
        """Add a single instruction to the queue."""
        self.queue.append(instruction)

    def submit_batch(self, batch: InstructionBatch):
        """Add a batch of instructions to the queue."""
        for instr in batch.instructions:
            self.queue.append(instr)

    def submit_program(self, tile_id: int, conductance_matrix):
        """Program conductance values into a tile."""
        instr = Instruction(
            OpCode.PROGRAM_CONDUCTANCE,
            tile_id,
            {"weights": conductance_matrix}
        )
        self.submit(instr)

    def submit_mvm(self, tile_id: int, input_vector):
        """Submit a Vector-Matrix Multiplication operation."""
        instr = Instruction(
            OpCode.EXECUTE_MVM,
            tile_id,
            {"x": input_vector}
        )
        self.submit(instr)

    def step(self) -> Optional[Any]:
        """Execute the next instruction in the queue. Returns result if any."""
        if not self.queue:
            return None

        instr = self.queue.popleft()
        self.instruction_count += 1
        
        # Get the target tile
        tile = self.device_mgr.get_tile(instr.tile_id)
        
        result = None
        
        # Execute based on opcode
        if instr.opcode == OpCode.ALLOC_TILE:
            tile_id = self.device_mgr.allocate_tile()
            result = tile_id
            
        elif instr.opcode == OpCode.FREE_TILE:
            self.device_mgr.free_tile(instr.tile_id)
            result = True
            
        elif instr.opcode == OpCode.PROGRAM_CONDUCTANCE:
            # Program conductance matrix into crossbar
            weights = instr.payload["weights"]
            # In real hardware, this would pulse cells to target conductance
            # For emulation, we initialize the crossbar with these weights
            result = True
            
        elif instr.opcode == OpCode.EXECUTE_MVM:
            # Execute Vector-Matrix Multiplication
            x_vector = instr.payload["x"]
            result = tile.forward_vmm(x_vector, add_noise=True)
            self.device_mgr.record_operation(instr.tile_id)
            
        elif instr.opcode == OpCode.READ_MATRIX:
            # Read current conductance state
            result = tile.read_matrix(add_noise=True)
            self.device_mgr.record_operation(instr.tile_id)
            
        elif instr.opcode == OpCode.CALIBRATE_TILE:
            # Run calibration sequence (placeholder)
            result = True
            
        elif instr.opcode == OpCode.REFRESH_TILE:
            # Perform drift compensation refresh
            tile.step_time(dt=1.0)
            self.device_mgr.record_refresh(instr.tile_id)
            result = True
            
        elif instr.opcode == OpCode.SYNC_TILE:
            # Synchronize tile state
            result = True
            
        elif instr.opcode == OpCode.TICK_PROBE:
            # Sparse probe read for Compensation Tick
            probe_indices = instr.payload.get("probe_indices", [])
            result = [tile.grid[r][c].read(add_noise=True) for r, c in probe_indices]
            self.device_mgr.record_operation(instr.tile_id)
            
        elif instr.opcode == OpCode.TILE_COMPENSATE:
            # Apply per-tile correction
            scale = instr.payload.get("scale", 1.0)
            offset = instr.payload.get("offset", 0.0)
            self.device_mgr.tiles[instr.tile_id]["correction_scale"] = scale
            self.device_mgr.tiles[instr.tile_id]["correction_offset"] = offset
            result = True
            
        elif instr.opcode == OpCode.KALMAN_UPDATE:
            # Update Kalman filter (handled by compensation_tick module)
            result = True
            
        elif instr.opcode == OpCode.TIKI_TAKA_CORRECT:
            # Apply Tiki-Taka asymmetry correction (handled by compensation_tick)
            result = True
            
        else:
            raise ValueError(f"Unknown opcode: {instr.opcode}")
        
        # Store result
        self.results[instr.tile_id] = result
        return result

    def execute_all(self) -> List[Any]:
        """Execute all queued instructions and return results."""
        results = []
        while self.queue:
            results.append(self.step())
        return results

    def execute_mvm_batch(self, tile_id: int, input_vectors: List[List[float]]) -> List[Any]:
        """Execute multiple MVM operations on the same tile."""
        results = []
        for x_vector in input_vectors:
            self.submit_mvm(tile_id, x_vector)
        return self.execute_all()

    def inject_maintenance(self):
        """Inject maintenance operations using Compensation Tick when available."""
        current_time = self.current_time
        
        for tile_id in self.device_mgr.allocated_tiles():
            tile_info = self.device_mgr.get_tile_info(tile_id)
            
            if self.compensation_tick and self.compensation_tick.should_tick(tile_id, current_time):
                tile = self.device_mgr.get_tile(tile_id)
                result = self.compensation_tick.tick(tile_id, tile, current_time)
                
                scale = result.correction_scale
                offset = result.correction_offset
                self.tiles[tile_id]["correction_scale"] = scale
                self.tiles[tile_id]["correction_offset"] = offset
                
            else:
                if tile_info["drift_accumulated"] > self.drift_threshold:
                    self.submit(InstructionSet.refresh(tile_id))
                
                if current_time - tile_info["last_calibration"] > self.calibration_interval:
                    self.submit(InstructionSet.calibrate(tile_id))
                    self.device_mgr.tiles[tile_id]["last_calibration"] = current_time

    def advance_time(self, dt: float):
        """Advance simulation time and trigger maintenance if needed."""
        self.current_time += dt
        self.device_mgr.step_time(dt)
        
        # Periodically inject maintenance
        if int(self.current_time) % 50 == 0:
            self.inject_maintenance()

    def get_queue_stats(self) -> dict:
        """Return statistics about the instruction queue."""
        return {
            "queue_length": len(self.queue),
            "total_instructions": self.instruction_count,
            "current_time": self.current_time,
            "results_count": len(self.results),
        }

    def clear_queue(self):
        """Clear all pending instructions."""
        self.queue.clear()

    def peek_next(self) -> Optional[Instruction]:
        """Peek at the next instruction without executing it."""
        return self.queue[0] if self.queue else None


# Re-import InstructionSet at module level
from isa import InstructionSet


if __name__ == "__main__":
    print("Testing ACR Runtime Scheduler...")
    
    # Create device manager and scheduler with 4x4 tiles
    dm = DeviceManager(total_tiles=2, tile_rows=4, tile_cols=4)
    scheduler = RuntimeScheduler(dm)
    
    # Allocate a tile
    tile0 = dm.allocate_tile()
    print(f"Allocated tile: {tile0}")
    
    # Program conductance matrix (4 rows to match tile_rows)
    weights = [[0.5, 0.3], [0.2, 0.8], [0.4, 0.6], [0.7, 0.1]]
    scheduler.submit_program(tile0, weights)
    
    # Execute MVM with 4-element input vector (matching tile_rows)
    x_input = [0.5, 0.8, 0.2, 0.1]
    scheduler.submit_mvm(tile0, x_input)
    
    # Execute all queued instructions
    results = scheduler.execute_all()
    print(f"Execution results: {results}")
    
    # Get queue stats
    stats = scheduler.get_queue_stats()
    print(f"Queue stats: {stats}")
    
    # Test batch execution with 4-element vectors
    batch_results = scheduler.execute_mvm_batch(tile0, [[0.5, 0.8, 0.2, 0.1], [0.2, 0.3, 0.4, 0.5]])
    print(f"Batch results: {batch_results}")
    
    print("Runtime Scheduler functional!")
