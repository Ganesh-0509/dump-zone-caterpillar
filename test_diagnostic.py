#!/usr/bin/env python
"""Detailed diagnostic for stuck trucks."""

from app import initialize_simulation, simulation_state

# Initialize
print("Initializing simulation...")
initialize_simulation()

engine = simulation_state['engine']
print(f"Engine with {len(engine.zones)} zones")
print(f"Approach lane: {engine.approach_lane_point}")
print()

# Run steps and monitor trucks
for step in range(20):
    engine.step()
    
    if step % 2 == 0 and len(engine.trucks) > 0:
        print(f"\n=== STEP {step} ({len(engine.trucks)} trucks) ===")
        for truck in engine.trucks[:3]:  # Only show first 3
            print(f"\nTruck {truck.truck_id}:")
            print(f"  Pos: ({truck.position_x:.1f}, {truck.position_y:.1f})")
            print(f"  State: {truck.state.value}")
            print(f"  Target: ({truck.target_x:.1f}, {truck.target_y:.1f})")
            print(f"  Approach stage: {truck.approach_stage}")
            print(f"  Path: {len(truck.path)} nodes, index={truck.current_path_index}")
            
            if truck.path and truck.current_path_index < len(truck.path):
                next_node = truck.path[truck.current_path_index]
                print(f"  Next path node: {next_node}")
                grid_val = engine.occupancy_grid[next_node[1], next_node[0]]
                print(f"  Grid value at next node: {grid_val}")
            
            print(f"  Distance to target: {((truck.target_x - truck.position_x)**2 + (truck.target_y - truck.position_y)**2)**0.5:.1f}")
