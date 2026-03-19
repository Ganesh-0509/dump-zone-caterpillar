#!/usr/bin/env python
"""Detailed test to diagnose truck movement issues."""

from app import initialize_simulation, simulation_state

# Initialize
print("Initializing simulation...")
initialize_simulation()

engine = simulation_state['engine']
print(f"Engine created with {len(engine.zones)} zones")
print(f"Approach lane: {engine.approach_lane_point}")
print(f"Return lane: {engine.return_lane_point}")
print(f"Exit point: {engine.exit_point}\n")

for i in range(30):
    engine.step()
    truck_count = len(engine.trucks)
    
    if i % 5 == 0 or truck_count > 0:
        print(f"Step {i}: {truck_count} trucks active, queued={engine.generator.queued_loads}")
        
        for truck in engine.trucks:
            print(f"  Truck {truck.truck_id}:")
            print(f"    Position: ({truck.position_x:.1f}, {truck.position_y:.1f})")
            print(f"    State: {truck.state.value}")
            print(f"    Target: ({truck.target_x:.1f}, {truck.target_y:.1f})")
            print(f"    Path length: {len(truck.path)}, index: {truck.current_path_index}")
            print(f"    Approach stage: {truck.approach_stage}, waiting: {truck.waiting_for_dump_slot}")
            print(f"    Has dump spot: {truck.has_dump_spot}")

print(f"\nTotal trucks spawned: {engine.generator.truck_counter}")
print(f"Total dumps: {sum(1 for cell in engine.occupancy_grid.flat if cell == 1)}")
