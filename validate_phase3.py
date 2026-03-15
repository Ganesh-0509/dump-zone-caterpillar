"""Validate Phase-3 truck simulation layer."""

from __future__ import annotations

from pathlib import Path

from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig
from simulation.truck_agent import TruckState


def validate_truck_agent() -> bool:
    """Verify truck movement logic."""
    print("\n=== TRUCK AGENT ===")

    from simulation.truck_agent import Truck

    truck = Truck(
        truck_id=0,
        position_x=0.0,
        position_y=0.0,
        speed=1.0,
        target_x=10.0,
        target_y=0.0,
    )

    # Move truck 5 times
    for _ in range(5):
        reached = truck.move_toward_target()
        assert not reached, "Truck should not reach target yet"

    assert 4.9 < truck.position_x <= 5.0, f"Truck X position wrong: {truck.position_x}"
    print(f"✓ Truck movement correct: position=({truck.position_x:.2f}, {truck.position_y:.2f})")

    # Move truck to target
    for _ in range(10):
        reached = truck.move_toward_target()
        if reached:
            break

    assert truck.position_x == 10.0 and truck.position_y == 0.0, "Truck should snap to target"
    print(f"✓ Truck reached target and snapped: position=({truck.position_x:.2f}, {truck.position_y:.2f})")

    return True


def validate_truck_spawning() -> bool:
    """Verify truck spawning and zone assignment."""
    print("\n=== TRUCK SPAWNING ===")

    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"

    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=4, random_seed=42)
    zones = generate_voronoi_zones(dump_polygon, zone_config)

    from simulation.truck_generator import TruckGenerator

    gen_config = TruckGeneratorConfig(spawn_interval=10, truck_speed=0.5)
    generator = TruckGenerator(zones, gen_config)

    # Spawn trucks
    spawned_trucks = []
    for i in range(30):
        if generator.should_spawn(i):
            truck = generator.spawn_truck()
            spawned_trucks.append(truck)

    assert len(spawned_trucks) == 2, f"Expected 2 spawned trucks, got {len(spawned_trucks)}"
    print(f"✓ Truck spawning on interval: spawned {len(spawned_trucks)} trucks")

    # Check round-robin assignment
    for truck in spawned_trucks:
        assert truck.assigned_zone is not None, f"Truck {truck.truck_id} has no assigned zone"
        zone_index = truck.truck_id % len(zones)
        target_zone = zones[zone_index]
        assert truck.assigned_zone == target_zone, f"Zone assignment wrong for truck {truck.truck_id}"

    print(f"✓ Round-robin zone assignment correct")
    print(f"  - Truck 0 assigned to zone {0 % len(zones)}")
    print(f"  - Truck 1 assigned to zone {1 % len(zones)}")

    return True


def validate_simulation_engine() -> bool:
    """Verify simulation loop and truck updates."""
    print("\n=== SIMULATION ENGINE ===")

    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"

    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=4, random_seed=42)
    zones = generate_voronoi_zones(dump_polygon, zone_config)

    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=1.0)
    height_map = initialize_height_map(grid.shape)

    gen_config = TruckGeneratorConfig(spawn_interval=20, truck_speed=1.0)
    sim_config = SimulationConfig(max_steps=100, generator_config=gen_config)
    engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)

    engine.run()

    assert engine.current_step == 100, f"Expected 100 steps, got {engine.current_step}"
    assert len(engine.trucks) > 0, "No trucks spawned"

    print(f"✓ Simulation loop executed")
    print(f"  - Completed {engine.current_step} steps")
    print(f"  - Total trucks spawned: {len(engine.trucks)}")

    stats = engine.get_statistics()
    print(f"  - Moving: {stats['moving']}")
    print(f"  - Dumping: {stats['dumping']}")
    print(f"  - Returning: {stats['returning']}")
    print(f"  - Idle: {stats['idle']}")

    # Verify state transitions
    for truck in engine.trucks:
        assert truck.state in [TruckState.IDLE, TruckState.MOVING_TO_ZONE, TruckState.DUMPING, TruckState.RETURNING], \
            f"Invalid truck state: {truck.state}"

    print(f"✓ All truck states valid")

    return True


def main() -> None:
    """Run all Phase-3 validations."""
    print("\n" + "="*60)
    print("PHASE-3 TRUCK SIMULATION VALIDATION")
    print("="*60)

    try:
        validate_truck_agent()
        validate_truck_spawning()
        validate_simulation_engine()

        print("\n" + "="*60)
        print("✓ ALL PHASE-3 VALIDATIONS PASSED")
        print("="*60)
        print("\nTruck simulation layer is working correctly.")

    except AssertionError as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
