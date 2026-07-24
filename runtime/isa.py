"""
ACR Instruction Set Architecture (ISA) & Internal Representation

Decouples execution into discrete micro-instructions so the runtime can
execute against any backend (emulated or real chip).
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class OpCode(Enum):
    """Hardware operation opcodes for analog crossbar execution."""
    ALLOC_TILE = auto()           # Allocate a crossbar tile
    FREE_TILE = auto()            # Release a crossbar tile
    PROGRAM_CONDUCTANCE = auto()  # Load weights into crossbar
    EXECUTE_MVM = auto()          # Vector-Matrix Multiplication
    READ_MATRIX = auto()          # Read current conductance state
    CALIBRATE_TILE = auto()       # Run calibration sequence
    REFRESH_TILE = auto()         # Drift compensation refresh
    SYNC_TILE = auto()            # Synchronize tile state


@dataclass
class Instruction:
    """Single hardware instruction with opcode, target tile, and payload."""
    opcode: OpCode
    tile_id: int
    payload: Optional[Dict[str, Any]] = None
    priority: int = 0  # Higher = more urgent (e.g., refresh before drift critical)
    
    def __repr__(self):
        payload_str = f", payload={self.payload}" if self.payload else ""
        return f"Instruction({self.opcode.name}, tile={self.tile_id}{payload_str})"


@dataclass
class InstructionBatch:
    """Batch of instructions for optimized execution."""
    instructions: List[Instruction] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    def add(self, instruction: Instruction):
        self.instructions.append(instruction)
        return self
    
    def add_program(self, tile_id: int, conductance_matrix):
        """Add a PROGRAM_CONDUCTANCE instruction."""
        instr = InstructionSet.program_tile(tile_id, conductance_matrix)
        return self.add(instr)
    
    def add_mvm(self, tile_id: int, input_vector):
        """Add an EXECUTE_MVM instruction."""
        instr = InstructionSet.mvm(tile_id, input_vector)
        return self.add(instr)
    
    def add_refresh(self, tile_id: int):
        """Add a REFRESH_TILE instruction."""
        instr = InstructionSet.refresh(tile_id)
        return self.add(instr)


class InstructionSet:
    """Factory methods for creating typed instructions."""
    
    @staticmethod
    def alloc_tile(tile_id: int) -> Instruction:
        return Instruction(OpCode.ALLOC_TILE, tile_id)
    
    @staticmethod
    def free_tile(tile_id: int) -> Instruction:
        return Instruction(OpCode.FREE_TILE, tile_id)
    
    @staticmethod
    def program_tile(tile_id: int, conductance_matrix) -> Instruction:
        return Instruction(
            OpCode.PROGRAM_CONDUCTANCE,
            tile_id,
            {"weights": conductance_matrix}
        )
    
    @staticmethod
    def mvm(tile_id: int, input_vector) -> Instruction:
        return Instruction(
            OpCode.EXECUTE_MVM,
            tile_id,
            {"x": input_vector}
        )
    
    @staticmethod
    def read_matrix(tile_id: int) -> Instruction:
        return Instruction(OpCode.READ_MATRIX, tile_id)
    
    @staticmethod
    def calibrate(tile_id: int) -> Instruction:
        return Instruction(
            OpCode.CALIBRATE_TILE,
            tile_id,
            priority=10  # High priority
        )
    
    @staticmethod
    def refresh(tile_id: int) -> Instruction:
        return Instruction(
            OpCode.REFRESH_TILE,
            tile_id,
            priority=5  # Medium priority
        )
    
    @staticmethod
    def sync(tile_id: int) -> Instruction:
        return Instruction(OpCode.SYNC_TILE, tile_id)


if __name__ == "__main__":
    print("Testing ACR ISA...")
    
    # Create individual instructions
    prog = InstructionSet.program_tile(0, [[0.5, 0.3], [0.2, 0.8]])
    mvm = InstructionSet.mvm(0, [0.5, 0.8])
    refresh = InstructionSet.refresh(0)
    
    print(f"Program instruction: {prog}")
    print(f"MVM instruction: {mvm}")
    print(f"Refresh instruction: {refresh}")
    
    # Test batch creation
    batch = InstructionBatch()
    batch.add_program(0, [[0.5, 0.3], [0.2, 0.8]])
    batch.add_mvm(0, [0.5, 0.8])
    batch.add_refresh(0)
    
    print(f"\nBatch has {len(batch.instructions)} instructions")
    for i, instr in enumerate(batch.instructions):
        print(f"  {i}: {instr}")
    
    print("\nISA functional!")
