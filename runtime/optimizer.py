"""
AIMC Analog Runtime Optimizer (ARO)

The optimizer makes intelligent decisions about:
- Should this update happen?
- Should it be delayed?
- Should several updates be merged?
- Should we recalibrate?
- Should we refresh?
- Should we migrate this weight?
- Should we use another tile?

This moves the runtime from reactive to adaptive.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np


class OptimizationDecision(Enum):
    """Possible optimization decisions."""
    EXECUTE = "execute"
    DELAY = "delay"
    MERGE = "merge"
    RECALIBRATE = "recalibrate"
    REFRESH = "refresh"
    MIGRATE = "migrate"
    SKIP = "skip"


@dataclass
class OptimizationContext:
    """Context for optimization decisions."""
    tile_id: int
    current_time: float
    drift_exponent: float
    last_calibration_time: float
    error_rate: float
    update_frequency: float
    tile_health: float
    pending_updates: int
    energy_budget: float


@dataclass
class OptimizationResult:
    """Result of an optimization decision."""
    decision: OptimizationDecision
    confidence: float
    reason: str
    parameters: Dict
    estimated_benefit: float


class AnalogRuntimeOptimizer:
    """
    Makes intelligent decisions about runtime operations.

    The optimizer considers:
    - Current device state (drift, error rate, health)
    - Historical patterns (update frequency, calibration history)
    - Energy constraints (budget, efficiency targets)
    - Performance requirements (latency, accuracy)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.decision_history: List[OptimizationResult] = []
        self.performance_metrics: Dict[int, Dict] = {}

    def should_update_weight(self, context: OptimizationContext,
                             weight_delta: float) -> OptimizationResult:
        """
        Decide whether to execute a weight update.

        Considers:
        - Is the delta significant enough?
        - Is the tile in good health?
        - Are there energy constraints?
        """
        if abs(weight_delta) < 0.001:
            return OptimizationResult(
                decision=OptimizationDecision.SKIP,
                confidence=0.9,
                reason="Weight delta too small to be significant",
                parameters={"delta": weight_delta},
                estimated_benefit=0.0
            )

        if context.tile_health < 0.3:
            return OptimizationResult(
                decision=OptimizationDecision.RECALIBRATE,
                confidence=0.8,
                reason="Tile health is critical, recalibrate first",
                parameters={"health": context.tile_health},
                estimated_benefit=0.5
            )

        if context.error_rate > 0.1:
            return OptimizationResult(
                decision=OptimizationDecision.DELAY,
                confidence=0.7,
                reason="High error rate, delay update until stable",
                parameters={"error_rate": context.error_rate},
                estimated_benefit=0.3
            )

        return OptimizationResult(
            decision=OptimizationDecision.EXECUTE,
            confidence=0.85,
            reason="Update is significant and tile is healthy",
            parameters={"delta": weight_delta},
            estimated_benefit=abs(weight_delta)
        )

    def should_merge_updates(self, updates: List[float],
                             context: OptimizationContext) -> OptimizationResult:
        """
        Decide whether to merge multiple pending updates.

        Merging reduces the number of write operations,
        saving energy and reducing wear.
        """
        if len(updates) < 2:
            return OptimizationResult(
                decision=OptimizationDecision.EXECUTE,
                confidence=1.0,
                reason="Only one update, no merging needed",
                parameters={"count": len(updates)},
                estimated_benefit=0.0
            )

        net_delta = sum(updates)
        if abs(net_delta) < 0.01:
            return OptimizationResult(
                decision=OptimizationDecision.MERGE,
                confidence=0.85,
                reason=f"Updates largely cancel out (net={net_delta:.4f})",
                parameters={"count": len(updates), "net_delta": net_delta},
                estimated_benefit=len(updates) * 0.1
            )

        return OptimizationResult(
            decision=OptimizationDecision.EXECUTE,
            confidence=0.7,
            reason="Updates are additive, execute sequentially",
            parameters={"count": len(updates)},
            estimated_benefit=abs(net_delta)
        )

    def should_refresh_tile(self, context: OptimizationContext) -> OptimizationResult:
        """
        Decide whether to refresh a tile's conductances.

        Refreshing compensates for drift but costs energy.
        """
        time_since_calibration = context.current_time - context.last_calibration_time

        critical_time = 1.0 / (context.drift_exponent + 0.001) * 0.1

        if time_since_calibration > critical_time:
            return OptimizationResult(
                decision=OptimizationDecision.REFRESH,
                confidence=0.9,
                reason=f"Drift exceeds threshold ({time_since_calibration:.1f} > {critical_time:.1f})",
                parameters={"time_since_cal": time_since_calibration, "critical_time": critical_time},
                estimated_benefit=0.5
            )

        if context.error_rate > 0.15:
            return OptimizationResult(
                decision=OptimizationDecision.REFRESH,
                confidence=0.8,
                reason=f"Error rate too high ({context.error_rate:.2%})",
                parameters={"error_rate": context.error_rate},
                estimated_benefit=0.4
            )

        return OptimizationResult(
            decision=OptimizationDecision.SKIP,
            confidence=0.85,
            reason="Tile is within acceptable parameters",
            parameters={"time_since_cal": time_since_calibration},
            estimated_benefit=0.0
        )

    def should_migrate_weight(self, source_tile: int, target_tile: int,
                              context: OptimizationContext) -> OptimizationResult:
        """
        Decide whether to migrate a weight to another tile.

        Migration can improve reliability or balance wear.
        """
        if context.tile_health < 0.2:
            return OptimizationResult(
                decision=OptimizationDecision.MIGRATE,
                confidence=0.9,
                reason="Source tile health is critical",
                parameters={"source": source_tile, "target": target_tile},
                estimated_benefit=0.6
            )

        if context.tile_health > 0.8:
            return OptimizationResult(
                decision=OptimizationDecision.SKIP,
                confidence=0.85,
                reason="Source tile is healthy, no migration needed",
                parameters={"source": source_tile, "target": target_tile},
                estimated_benefit=0.0
            )

        return OptimizationResult(
            decision=OptimizationDecision.SKIP,
            confidence=0.7,
            reason="Tile health is acceptable, defer migration",
            parameters={"source": source_tile, "target": target_tile},
            estimated_benefit=0.1
        )

    def optimize_batch(self, operations: List[Dict],
                       context: OptimizationContext) -> List[OptimizationResult]:
        """
        Optimize a batch of operations.

        This is the main entry point for the optimizer.
        It analyzes a batch and makes holistic decisions.
        """
        results = []

        weight_updates = [op for op in operations if op.get("type") == "weight_update"]
        if weight_updates:
            deltas = [op.get("delta", 0) for op in weight_updates]
            merge_result = self.should_merge_updates(deltas, context)
            results.append(merge_result)

        refresh_needed = any(op.get("type") == "refresh" for op in operations)
        if not refresh_needed:
            refresh_result = self.should_refresh_tile(context)
            if refresh_result.decision == OptimizationDecision.REFRESH:
                results.append(refresh_result)

        for op in operations:
            if op.get("type") == "weight_update":
                result = self.should_update_weight(context, op.get("delta", 0))
                results.append(result)

        self.decision_history.extend(results)
        return results

    def get_performance_report(self) -> Dict:
        """Get performance metrics for the optimizer."""
        if not self.decision_history:
            return {"total_decisions": 0}

        decisions = [r.decision.value for r in self.decision_history]
        confidences = [r.confidence for r in self.decision_history]

        return {
            "total_decisions": len(self.decision_history),
            "decision_distribution": {d: decisions.count(d) for d in set(decisions)},
            "avg_confidence": np.mean(confidences),
            "total_benefit": sum(r.estimated_benefit for r in self.decision_history),
        }
