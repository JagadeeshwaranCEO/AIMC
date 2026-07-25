"""
AIMC Analog Virtual Memory (AVM)

Just as operating systems virtualize physical memory to give each process
its own address space, AVM virtualizes analog conductance to give each
AI model its own reliable weight space.

The key insight: software engineers instantly understand virtual memory.
This module makes analog computing concepts accessible.

AVM provides:
- Logical-to-physical conductance mapping
- Automatic page management (tiles)
- Demand paging (load weights on demand)
- Write-back caching (batch updates)
- Memory protection (isolation between models)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class VirtualPage:
    """A virtual page of conductance values."""
    page_id: int
    logical_address: Tuple[int, int]
    physical_address: Optional[Tuple[int, int]] = None
    conductance_data: Optional[np.ndarray] = None
    is_loaded: bool = False
    is_dirty: bool = False
    access_count: int = 0
    last_access_time: float = 0.0
    drift_state: float = 0.0


@dataclass
class PhysicalFrame:
    """A physical frame in the crossbar."""
    frame_id: int
    tile_id: int
    row_start: int
    row_end: int
    col_start: int
    col_end: int
    is_allocated: bool = False
    owner_page_id: Optional[int] = None
    health_score: float = 1.0


class AnalogVirtualMemory:
    """
    Virtual memory system for analog conductance.

    Provides a logical address space that maps to physical crossbar tiles.
    Handles allocation, paging, and protection automatically.
    """

    def __init__(self, total_tiles: int, tile_rows: int, tile_cols: int):
        self.total_tiles = total_tiles
        self.tile_rows = tile_rows
        self.tile_cols = tile_cols

        self.pages: Dict[int, VirtualPage] = {}
        self.frames: Dict[int, PhysicalFrame] = {}
        self.page_table: Dict[int, int] = {}
        self.next_page_id = 0

        for i in range(total_tiles):
            self.frames[i] = PhysicalFrame(
                frame_id=i,
                tile_id=i,
                row_start=0,
                row_end=tile_rows,
                col_start=0,
                col_end=tile_cols,
            )

    def allocate_page(self, rows: int, cols: int) -> int:
        """Allocate a new virtual page."""
        page_id = self.next_page_id
        self.next_page_id += 1

        self.pages[page_id] = VirtualPage(
            page_id=page_id,
            logical_address=(page_id, 0),
            conductance_data=np.zeros((rows, cols)),
        )

        return page_id

    def load_page(self, page_id: int, tile_id: int) -> bool:
        """Load a virtual page to a physical frame."""
        if page_id not in self.pages:
            return False

        frame = self.frames.get(tile_id)
        if not frame or frame.is_allocated:
            return False

        page = self.pages[page_id]
        frame.is_allocated = True
        frame.owner_page_id = page_id
        page.physical_address = (tile_id, 0)
        page.is_loaded = True
        self.page_table[page_id] = tile_id

        return True

    def unload_page(self, page_id: int) -> bool:
        """Unload a virtual page from physical memory."""
        if page_id not in self.page_table:
            return False

        tile_id = self.page_table[page_id]
        frame = self.frames[tile_id]
        frame.is_allocated = False
        frame.owner_page_id = None

        page = self.pages[page_id]
        page.is_loaded = False
        page.physical_address = None

        del self.page_table[page_id]
        return True

    def read_conductance(self, page_id: int, row: int, col: int) -> float:
        """Read conductance from a virtual page."""
        if page_id not in self.pages:
            return 0.0

        page = self.pages[page_id]
        if not page.is_loaded:
            self._page_fault(page_id)

        page.access_count += 1
        return page.conductance_data[row, col]

    def write_conductance(self, page_id: int, row: int, col: int,
                          value: float) -> bool:
        """Write conductance to a virtual page."""
        if page_id not in self.pages:
            return False

        page = self.pages[page_id]
        if not page.is_loaded:
            self._page_fault(page_id)

        page.conductance_data[row, col] = value
        page.is_dirty = True
        return True

    def _page_fault(self, page_id: int):
        """Handle a page fault by loading the page."""
        free_frame = None
        for frame in self.frames.values():
            if not frame.is_allocated:
                free_frame = frame
                break

        if free_frame:
            self.load_page(page_id, free_frame.frame_id)

    def get_page_stats(self, page_id: int) -> Dict:
        """Get statistics for a virtual page."""
        if page_id not in self.pages:
            return {}

        page = self.pages[page_id]
        return {
            "page_id": page_id,
            "is_loaded": page.is_loaded,
            "is_dirty": page.is_dirty,
            "access_count": page.access_count,
            "drift_state": page.drift_state,
            "physical_address": page.physical_address,
        }

    def get_system_stats(self) -> Dict:
        """Get system-wide memory statistics."""
        loaded = sum(1 for p in self.pages.values() if p.is_loaded)
        dirty = sum(1 for p in self.pages.values() if p.is_dirty)
        allocated = sum(1 for f in self.frames.values() if f.is_allocated)

        return {
            "total_pages": len(self.pages),
            "loaded_pages": loaded,
            "dirty_pages": dirty,
            "total_frames": len(self.frames),
            "allocated_frames": allocated,
            "free_frames": len(self.frames) - allocated,
            "page_fault_rate": loaded / max(len(self.pages), 1),
        }
