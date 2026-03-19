#!/usr/bin/env python
"""Quick test to verify trucks are moving."""

from app import initialize_simulation, simulation_state

# Initialize
print("Initializing simulation...")
initialize_simulation()

# Run a few steps
engine = simulation_state['engine']
print(f"Engine created with {len(engine.zones)} zones\n")

for i in range(5):
    engine.step()
    truck_count = len(engine.trucks)
    print(f"Step {i}: {truck_count} trucks active")
    if truck_count > 0:
        truck = engine.trucks[0]
        print(f"  Truck 0: pos=({truck.position_x:.1f}, {truck.position_y:.1f}), state={truck.state.value}, has_path={len(truck.path) > 0}")

print(f"\nTotal trucks spawned: {engine.generator.truck_counter}")
