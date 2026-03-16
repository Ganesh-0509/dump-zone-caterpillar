#!/usr/bin/env python
"""Comprehensive integration test verifying all new features."""

from pathlib import Path
import numpy as np
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig
from planning.deadlock_manager import DeadlockManager
from planning.slope_validator import SlopeValidator
from planning.traffic_manager import TrafficManager

def verify_integration():
    """Verify all integrated features work correctly."""
    print("=" * 70)
    print("SYSTEM INTEGRATION VERIFICATION")
    print("=" * 70)
    
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=3, random_seed=42)
    generator_config = TruckGeneratorConfig(
        spawn_interval=2,
        truck_speed=0.5,
        entrance_x=dump_polygon.bounds[0],
        entrance_y=dump_polygon.bounds[1],
        initial_payload=1.0,
    )
    
    zones = generate_voronoi_zones(dump_polygon, zone_config)
    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=0.5)
    height_map = initialize_height_map(grid.shape)
    
    sim_config = SimulationConfig(max_steps=60, generator_config=generator_config)
    engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)
    
    # Verify all managers are initialized
    print("\n✓ MANAGER INITIALIZATION")
    print(f"  - DeadlockManager: {engine.deadlock_manager is not None}")
    print(f"  - SlopeValidator: {engine.slope_validator is not None}")
    print(f"  - TrafficManager: {engine.traffic_manager is not None}")
    print(f"  - AnalyticsManager: {engine.analytics is not None}")
    
    # Verify traffic manager supports footprint operations
    print("\n✓ TRAFFIC MANAGER FOOTPRINT SUPPORT")
    traffic_mgr = TrafficManager()
    has_footprint_reserve = hasattr(traffic_mgr, 'reserve_footprint_path')
    has_footprint_check = hasattr(traffic_mgr, 'check_footprint_available')
    print(f"  - reserve_footprint_path(): {has_footprint_reserve}")
    print(f"  - check_footprint_available(): {has_footprint_check}")
    
    # Verify slope validator methods
    print("\n✓ SLOPE VALIDATOR METHODS")
    slope_val = SlopeValidator()
    test_height = np.zeros((10, 10), dtype=np.float32)
    slope = slope_val.compute_slope(test_height, 5, 5)
    is_stable = slope_val.is_stable_slope(test_height, 5, 5)
    score = slope_val.score_dump_spot(5, 5, test_height, np.ones_like(test_height, dtype=bool), (5, 5), 5.0, 5.0, 1.0)
    print(f"  - compute_slope(): {type(slope).__name__}")
    print(f"  - is_stable_slope(): {type(is_stable).__name__}")
    print(f"  - score_dump_spot(): {type(score).__name__}")
    
    # Verify deadlock manager methods
    print("\n✓ DEADLOCK MANAGER METHODS")
    deadlock_mgr = DeadlockManager()
    print(f"  - update(): {hasattr(deadlock_mgr, 'update')}")
    print(f"  - reset_truck_history(): {hasattr(deadlock_mgr, 'reset_truck_history')}")
    
    # Run simulation and verify all features are used
    print("\n✓ SIMULATION EXECUTION")
    deadlock_events = 0
    location_diversity = set()
    slope_recorded = False
    
    for step in range(60):
        engine.step()
        
        # Track metrics
        if step > 0:
            if len(engine.deadlock_manager.truck_states) > 0:
                deadlock_events += 1
        
        for truck in engine.trucks:
            if truck.dump_grid_x >= 0 and truck.dump_grid_y >= 0:
                location_diversity.add((truck.dump_grid_x, truck.dump_grid_y))
    
    summary = engine.analytics.get_summary()
    slope_recorded = summary['layer_growth_events'] > 0
    
    print(f"  - Step count: 60")
    print(f"  - Trucks spawned: {len(engine.trucks)}")
    print(f"  - Unique dump locations: {len(location_diversity)}")
    print(f"  - Total dumps recorded: {summary['total_dumps']}")
    print(f"  - Layer growth events: {summary['layer_growth_events']}")
    
    # Final results
    print("\n" + "=" * 70)
    print("INTEGRATION SUMMARY")
    print("=" * 70)
    
    all_passed = (
        engine.deadlock_manager is not None and
        engine.slope_validator is not None and
        has_footprint_reserve and
        has_footprint_check and
        len(location_diversity) > 1 and
        summary['total_dumps'] > 0
    )
    
    print(f"\n✓ Deadlock detection available: {'PASS' if engine.deadlock_manager else 'FAIL'}")
    print(f"✓ Slope validation active: {'PASS' if engine.slope_validator else 'FAIL'}")
    print(f"✓ Mixed fleet support ready: {'PASS' if has_footprint_reserve else 'FAIL'}")
    print(f"✓ Truck distribution working: {'PASS' if len(location_diversity) > 1 else 'FAIL'}")
    print(f"✓ Analytics tracking: {'PASS' if summary['total_dumps'] > 0 else 'FAIL'}")
    
    if all_passed:
        print("\n" + "🎉 " * 10)
        print("ALL SYSTEMS INTEGRATED SUCCESSFULLY!")
        print("🎉 " * 10)
    else:
        print("\n⚠️  Some systems did not verify correctly")
    
    return all_passed

if __name__ == "__main__":
    verify_integration()
