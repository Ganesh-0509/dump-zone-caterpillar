#!/usr/bin/env python
"""Detailed state diagnostic for entry-point stuck trucks."""

from app import initialize_simulation, simulation_state

# Initialize
print("Initializing simulation...")
initialize_simulation()

engine = simulation_state['engine']
print(f"Engine config:")
print(f"  Entrance: ({engine.config.generator_config.entrance_x}, {engine.config.generator_config.entrance_y})")
print(f"  Approach lane: {engine.approach_lane_point}")
print(f"  Return lane: {engine.return_lane_point}")
print(f"  Exit point: {engine.exit_point}\n")

# Run simulation
for step in range(25):
    engine.step()
    
    if step == 24 and len(engine.trucks) > 0:
        print(f"\n=== STEP {step} ({len(engine.trucks)} trucks) ===\n")
        
        for i, truck in enumerate(engine.trucks[:3]):
            print(f"Truck {i} (ID={truck.truck_id}):")
            print(f"  Position: ({truck.position_x:.2f}, {truck.position_y:.2f})")
            print(f"  Target: ({truck.target_x:.2f}, {truck.target_y:.2f})")
            print(f"  State: {truck.state.value}")
            print(f"  Approach stage: {truck.approach_stage}")
            print(f"  Has dump spot: {truck.has_dump_spot}")
            print(f"  Dump location: ({truck.dump_grid_x}, {truck.dump_grid_y})")
            print(f"  Waiting for dump: {truck.waiting_for_dump_slot}")
            print(f"  Path: {len(truck.path)} nodes, current index: {truck.current_path_index}")
            
            if truck.path and truck.current_path_index < len(truck.path):
                node = truck.path[truck.current_path_index]
                print(f"  Next path node: {node}")
            
            dist_to_target = ((truck.target_x - truck.position_x)**2 + (truck.target_y - truck.position_y)**2)**0.5
            print(f"  Distance to target: {dist_to_target:.2f}")
            print()
