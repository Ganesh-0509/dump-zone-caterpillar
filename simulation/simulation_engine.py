"""Main simulation engine controlling truck movement and updates."""

from __future__ import annotations

from dataclasses import dataclass, field

from shapely.geometry import Polygon

from simulation.truck_agent import Truck, TruckState
from simulation.truck_generator import TruckGenerator, TruckGeneratorConfig


@dataclass
class SimulationConfig:
    """Configuration for the simulation engine."""

    max_steps: int = 500
    generator_config: TruckGeneratorConfig = field(default_factory=TruckGeneratorConfig)


class SimulationEngine:
    """Manages the truck simulation loop."""

    def __init__(self, zones: list[Polygon], config: SimulationConfig):
        if not zones:
            raise ValueError("zones list cannot be empty.")

        self.zones = zones
        self.config = config
        self.generator = TruckGenerator(zones, config.generator_config)
        self.trucks: list[Truck] = []
        self.current_step = 0
        self.history: list[dict] = []

    def step(self) -> None:
        """Execute one simulation step."""
        # Spawn new trucks if needed
        if self.generator.should_spawn(self.current_step):
            new_truck = self.generator.spawn_truck()
            self.trucks.append(new_truck)

        # Update all trucks
        for truck in self.trucks:
            if truck.state == TruckState.MOVING_TO_ZONE:
                target_reached = truck.move_toward_target()
                if target_reached:
                    truck.state = TruckState.DUMPING

            elif truck.state == TruckState.DUMPING:
                # Instant dump for this phase
                truck.payload = 0.0
                truck.state = TruckState.RETURNING

            elif truck.state == TruckState.RETURNING:
                # Return to entrance
                truck.set_target(
                    self.config.generator_config.entrance_x,
                    self.config.generator_config.entrance_y,
                )
                target_reached = truck.move_toward_target()
                if target_reached:
                    truck.state = TruckState.IDLE

        # Record state snapshot for visualization
        snapshot = {
            "step": self.current_step,
            "truck_count": len(self.trucks),
            "truck_positions": [(t.position_x, t.position_y) for t in self.trucks],
            "truck_states": [t.state.value for t in self.trucks],
        }
        self.history.append(snapshot)

        self.current_step += 1

    def run(self) -> None:
        """Run simulation for configured max_steps."""
        while self.current_step < self.config.max_steps:
            self.step()

    def get_current_trucks(self) -> list[Truck]:
        """Get all active trucks at current step."""
        return self.trucks.copy()

    def get_moving_trucks(self) -> list[Truck]:
        """Get trucks currently moving to zone."""
        return [t for t in self.trucks if t.state == TruckState.MOVING_TO_ZONE]

    def get_dumping_trucks(self) -> list[Truck]:
        """Get trucks currently dumping."""
        return [t for t in self.trucks if t.state == TruckState.DUMPING]

    def get_returning_trucks(self) -> list[Truck]:
        """Get trucks currently returning."""
        return [t for t in self.trucks if t.state == TruckState.RETURNING]

    def get_idle_trucks(self) -> list[Truck]:
        """Get idle trucks."""
        return [t for t in self.trucks if t.state == TruckState.IDLE]

    def get_statistics(self) -> dict:
        """Get simulation statistics."""
        return {
            "step": self.current_step,
            "total_trucks": len(self.trucks),
            "moving": len(self.get_moving_trucks()),
            "dumping": len(self.get_dumping_trucks()),
            "returning": len(self.get_returning_trucks()),
            "idle": len(self.get_idle_trucks()),
        }
