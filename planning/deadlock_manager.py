"""Deadlock detection and resolution for multi-truck coordination."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class TruckWaitState:
    """Track wait state for a truck."""
    truck_id: int
    wait_steps: int = 0
    blocked_by: set[int] = field(default_factory=set)
    last_position: tuple[float, float] = (0.0, 0.0)


class DeadlockManager:
    """Detects and resolves deadlocks in multi-truck operations."""

    def __init__(self, wait_threshold: int = 20, max_retries: int = 3):
        """
        Initialize deadlock manager.
        
        Args:
            wait_threshold: Trucks stationary for this many steps are considered stuck
            max_retries: Maximum times to retry resolving the same deadlock
        """
        self.wait_threshold = wait_threshold
        self.max_retries = max_retries
        self.truck_states: dict[int, TruckWaitState] = {}
        self.deadlock_history: dict[int, int] = defaultdict(int)  # truck_id -> retry count

    def update(self, trucks: list, traffic_manager) -> list[int]:
        """
        Update deadlock detection and return list of truck IDs to replan.
        
        Args:
            trucks: List of Truck objects
            traffic_manager: TrafficManager instance for reservation data
            
        Returns:
            List of truck IDs that should replan paths
        """
        stuck_trucks = []

        for truck in trucks:
            truck_id = truck.truck_id
            
            if truck_id not in self.truck_states:
                self.truck_states[truck_id] = TruckWaitState(
                    truck_id=truck_id,
                    last_position=(truck.position_x, truck.position_y)
                )
                continue

            state = self.truck_states[truck_id]
            
            # Check if truck moved
            dx = truck.position_x - state.last_position[0]
            dy = truck.position_y - state.last_position[1]
            distance_moved = (dx**2 + dy**2) ** 0.5
            
            if distance_moved < 0.1:  # Essentially stationary
                state.wait_steps += 1
            else:
                state.wait_steps = 0
                state.blocked_by.clear()
            
            state.last_position = (truck.position_x, truck.position_y)

            # Check if truck is waiting too long
            if state.wait_steps >= self.wait_threshold:
                stuck_trucks.append(truck_id)

        # Detect cycles in wait graph
        if stuck_trucks:
            cycles = self._detect_cycles(stuck_trucks, traffic_manager)
            
            for cycle in cycles:
                resolved = self._resolve_deadlock(cycle, trucks, traffic_manager)
                if resolved:
                    for truck_id in cycle:
                        self.deadlock_history[truck_id] += 1
                        stuck_trucks.append(truck_id)  # Mark for replan

        return stuck_trucks

    def _detect_cycles(
        self,
        stuck_truck_ids: list[int],
        traffic_manager,
    ) -> list[list[int]]:
        """
        Detect circular wait dependencies.
        
        Returns:
            List of cycles, each cycle is a list of truck IDs in circular dependency
        """
        cycles = []
        
        # Build wait graph for stuck trucks
        wait_graph = defaultdict(set)
        
        for truck_id in stuck_truck_ids:
            # For simplicity: if this truck is stuck, assume it's blocked by
            # whatever traffic is reserving cells ahead of it
            # (This is a simplified version; full implementation would inspect
            # actual next reserved cells for each truck)
            wait_graph[truck_id] = set()

        # Simplified cycle detection: any set of mutually stuck trucks
        # If all in a group are stationary and interdependent, mark as cycle
        if len(stuck_truck_ids) >= 2:
            # Treat all stuck trucks as forming a potential cycle
            cycles.append(stuck_truck_ids[:])

        return cycles

    def _resolve_deadlock(
        self,
        cycle: list[int],
        trucks: list,
        traffic_manager,
    ) -> bool:
        """
        Resolve a deadlock by selecting lowest priority truck to replan.
        
        Returns:
            True if deadlock was resolved, False otherwise
        """
        if not cycle:
            return False

        truck_dict = {t.truck_id: t for t in trucks}
        
        # Select lowest priority (lowest ID or least progress) truck to replan
        victim_truck_id = min(cycle)
        victim = truck_dict.get(victim_truck_id)

        if victim:
            # Clear reservations for this truck
            traffic_manager.release_reservations(victim_truck_id)
            
            # Mark for replan (will be handled by caller)
            victim.path = []
            victim.current_path_index = 0
            victim.current_smoothed_index = 0
            
            # Reset truck wait stats
            if victim_truck_id in self.truck_states:
                self.truck_states[victim_truck_id].wait_steps = 0

            return True

        return False

    def reset_truck_history(self, truck_id: int) -> None:
        """Reset deadlock history for a truck after successful path completion."""
        if truck_id in self.deadlock_history:
            del self.deadlock_history[truck_id]
        if truck_id in self.truck_states:
            self.truck_states[truck_id].wait_steps = 0
