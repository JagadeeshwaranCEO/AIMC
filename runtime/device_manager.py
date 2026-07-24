"""
ACR Device Manager
Tracks crossbar hardware tiles, allocation, and tile health.

Manages a pool of physical/emulated hardware tiles, tracking health,
thermal metrics, and allocation state - similar to a CUDA device manager.
"""
from typing import Dict, List, Optional, Tuple
from emulator import AnalogCrossbar2D


class DeviceManager:
    def __init__(self, total_tiles: int = 4, tile_rows: int = 16, tile_cols: int = 16):
        self.tile_rows = tile_rows
        self.tile_cols = tile_cols
        self.total_tiles = total_tiles
        
        # Initialize tile pool
        self.tiles: Dict[int, dict] = {
            i: {
                "crossbar": AnalogCrossbar2D(tile_rows, tile_cols, seed=42 + i * 1000),
                "allocated": False,
                "health_score": 1.0,
                "operation_count": 0,
                "last_calibration": 0.0,
                "drift_accumulated": 0.0,
                "drift_exponent": 0.01,
                "last_tick_time": 0.0,
                "tick_count": 0,
                "correction_scale": 1.0,
                "correction_offset": 0.0,
                "symmetry_point": 0.5,
                "gamma_up": 1.0,
                "gamma_down": 1.0,
            }
            for i in range(total_tiles)
        }
        
        # Statistics
        self.stats = {
            "total_allocations": 0,
            "total_deallocations": 0,
            "total_operations": 0,
            "total_refreshes": 0,
        }

    def allocate_tile(self) -> int:
        """
        Allocate an available crossbar tile.
        Returns tile_id or raises RuntimeError if no tiles available.
        """
        for tile_id, info in self.tiles.items():
            if not info["allocated"]:
                info["allocated"] = True
                self.stats["total_allocations"] += 1
                return tile_id
        raise RuntimeError("Out of hardware crossbar tiles!")

    def allocate_tiles(self, count: int) -> List[int]:
        """Allocate multiple tiles at once."""
        if count > self.available_tiles():
            raise RuntimeError(f"Requested {count} tiles but only {self.available_tiles()} available")
        
        allocated = []
        for _ in range(count):
            allocated.append(self.allocate_tile())
        return allocated

    def free_tile(self, tile_id: int):
        """Release a previously allocated tile."""
        if tile_id in self.tiles:
            if self.tiles[tile_id]["allocated"]:
                self.tiles[tile_id]["allocated"] = False
                self.stats["total_deallocations"] += 1
            else:
                raise ValueError(f"Tile {tile_id} is not currently allocated")

    def free_all_tiles(self):
        """Release all allocated tiles."""
        for tile_id in self.tiles:
            if self.tiles[tile_id]["allocated"]:
                self.free_tile(tile_id)

    def get_tile(self, tile_id: int) -> AnalogCrossbar2D:
        """Get the crossbar object for a specific tile."""
        if tile_id not in self.tiles:
            raise ValueError(f"Invalid tile_id: {tile_id}")
        return self.tiles[tile_id]["crossbar"]

    def get_tile_info(self, tile_id: int) -> dict:
        """Get metadata for a specific tile."""
        if tile_id not in self.tiles:
            raise ValueError(f"Invalid tile_id: {tile_id}")
        info = self.tiles[tile_id].copy()
        info.pop("crossbar")  # Don't include the actual crossbar object
        return info

    def available_tiles(self) -> int:
        """Return count of unallocated tiles."""
        return sum(1 for info in self.tiles.values() if not info["allocated"])

    def allocated_tiles(self) -> List[int]:
        """Return list of currently allocated tile IDs."""
        return [tile_id for tile_id, info in self.tiles.items() if info["allocated"]]

    def record_operation(self, tile_id: int):
        """Record that an operation was performed on a tile."""
        if tile_id in self.tiles:
            self.tiles[tile_id]["operation_count"] += 1
            self.stats["total_operations"] += 1

    def record_refresh(self, tile_id: int):
        """Record that a refresh was performed on a tile."""
        if tile_id in self.tiles:
            self.tiles[tile_id]["drift_accumulated"] = 0.0
            self.stats["total_refreshes"] += 1

    def update_health(self, tile_id: int, health_delta: float):
        """Update health score for a tile (range: 0.0 to 1.0)."""
        if tile_id in self.tiles:
            current = self.tiles[tile_id]["health_score"]
            self.tiles[tile_id]["health_score"] = max(0.0, min(1.0, current + health_delta))

    def get_system_stats(self) -> dict:
        """Return system-wide statistics."""
        return {
            **self.stats,
            "available_tiles": self.available_tiles(),
            "total_tiles": self.total_tiles,
            "tile_rows": self.tile_rows,
            "tile_cols": self.tile_cols,
        }

    def get_tile_health_summary(self) -> Dict[int, float]:
        """Return health scores for all tiles."""
        return {
            tile_id: info["health_score"]
            for tile_id, info in self.tiles.items()
        }

    def step_time(self, dt: float):
        """Advance time for all tiles (triggers drift simulation)."""
        for info in self.tiles.values():
            info["crossbar"].step_time(dt)
            info["drift_accumulated"] += dt

    def update_drift_state(self, tile_id: int, drift_exponent: float,
                           correction_scale: float, correction_offset: float):
        """
        Update drift state for a tile from Compensation Tick.
        """
        if tile_id in self.tiles:
            self.tiles[tile_id]["drift_exponent"] = drift_exponent
            self.tiles[tile_id]["correction_scale"] = correction_scale
            self.tiles[tile_id]["correction_offset"] = correction_offset
            self.tiles[tile_id]["last_tick_time"] = self.current_time if hasattr(self, 'current_time') else 0.0
            self.tiles[tile_id]["tick_count"] += 1

    def record_tick(self, tile_id: int):
        """Record that a Compensation Tick was executed on a tile."""
        if tile_id in self.tiles:
            self.tiles[tile_id]["tick_count"] += 1

    def get_drift_summary(self) -> Dict[int, Dict]:
        """Get drift state summary for all tiles."""
        return {
            tile_id: {
                "drift_exponent": info["drift_exponent"],
                "correction_scale": info["correction_scale"],
                "correction_offset": info["correction_offset"],
                "tick_count": info["tick_count"],
                "drift_accumulated": info["drift_accumulated"],
            }
            for tile_id, info in self.tiles.items()
            if info["allocated"]
        }


if __name__ == "__main__":
    print("Testing ACR Device Manager...")
    
    dm = DeviceManager(total_tiles=4, tile_rows=8, tile_cols=8)
    print(f"Created device with {dm.total_tiles} tiles ({dm.tile_rows}x{dm.tile_cols})")
    print(f"Available tiles: {dm.available_tiles()}")
    
    # Allocate some tiles
    tile0 = dm.allocate_tile()
    tile1 = dm.allocate_tile()
    print(f"Allocated tiles: {tile0}, {tile1}")
    print(f"Available tiles after allocation: {dm.available_tiles()}")
    
    # Get tile info
    info = dm.get_tile_info(tile0)
    print(f"Tile {tile0} info: {info}")
    
    # Record operations
    dm.record_operation(tile0)
    dm.record_operation(tile0)
    dm.record_operation(tile1)
    
    stats = dm.get_system_stats()
    print(f"System stats: {stats}")
    
    # Free tiles
    dm.free_tile(tile0)
    dm.free_tile(tile1)
    print(f"Available tiles after freeing: {dm.available_tiles()}")
    
    print("Device Manager functional!")
