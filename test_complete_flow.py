#!/usr/bin/env python3
"""Comprehensive test of simulation and coordinate pipeline."""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_complete_flow():
    """Test complete simulation flow with coordinate verification."""
    print("=" * 60)
    print("COMPREHENSIVE SIMULATION TEST")
    print("=" * 60)
    
    # 1. Initialize
    print("\n[1] Initializing simulation...")
    r = requests.post(f"{BASE_URL}/api/init")
    assert r.status_code == 200, f"Init failed: {r.text}"
    init_result = r.json()
    assert init_result['status'] == 'success'
    print("    ✓ Simulation initialized")
    
    # 2. Get metadata
    print("\n[2] Getting metadata...")
    r = requests.get(f"{BASE_URL}/api/metadata")
    assert r.status_code == 200
    meta = r.json()
    assert meta['status'] == 'success'
    b = meta['bounds']
    print(f"    Bounds: ({b['min_x']}, {b['min_y']}) to ({b['max_x']}, {b['max_y']})")
    print(f"    Zones: {meta['zones']}")
    assert b['min_x'] == 0 and b['max_x'] == 120
    assert b['min_y'] == 0 and b['max_y'] == 100
    print("    ✓ Metadata is correct")
    
    # 3. Run simulation
    print("\n[3] Running 30 simulation steps...")
    for i in range(30):
        r = requests.post(f"{BASE_URL}/api/step")
        assert r.status_code == 200
        if i % 10 == 0:
            print(f"    Step {i}...", end="", flush=True)
    print(" ✓ Complete")
    
    # 4. Check state
    print("\n[4] Checking simulation state...")
    r = requests.get(f"{BASE_URL}/api/state")
    assert r.status_code == 200
    state = r.json()
    assert state['status'] == 'success'
    
    trucks = state['trucks']
    print(f"    Active trucks: {len(trucks)}")
    print(f"    Total dumps: {state['metrics']['total_dumps']}")
    assert len(trucks) > 0, "No trucks spawned!"
    print("    ✓ Trucks are spawning")
    
    # 5. Verify truck positions
    print("\n[5] Verifying truck coordinates...")
    for truck in trucks[:3]:  # Check first 3 trucks
        x, y = truck['x'], truck['y']
        # Verify positions are within world bounds
        assert -10 < x < 130, f"Truck X out of bounds: {x}"
        assert -10 < y < 110, f"Truck Y out of bounds: {y}"
        
        # Test frontend transform
        canvas_w, canvas_h = 800, 600
        wr = 120.0
        hr = 100.0
        sx = canvas_w / wr
        sy = canvas_h / hr
        s = min(sx, sy) * 0.95
        ox = (canvas_w - wr * s) / 2
        oy = (canvas_h - hr * s) / 2
        screen_x = ox + (x - b['min_x']) * s
        screen_y = oy + (y - b['min_y']) * s
        
        assert 0 <= screen_x <= canvas_w, f"Screen X out of canvas: {screen_x}"
        assert 0 <= screen_y <= canvas_h, f"Screen Y out of canvas: {screen_y}"
        print(f"    Truck {truck['id']:2d}: world({x:6.1f}, {y:6.1f}) -> screen({screen_x:6.0f}, {screen_y:6.0f}) ✓")
    
    # 6. Check dump piles
    print("\n[6] Verifying dump piles...")
    dump_cells = state['dump_cells']
    if dump_cells:
        print(f"    Dump cells placed: {len(dump_cells)}")
        cell = dump_cells[0]
        cx, cy = cell['x'], cell['y']
        assert -10 < cx < 130, f"Dump cell X out of bounds: {cx}"
        assert -10 < cy < 110, f"Dump cell Y out of bounds: {cy}"
        print(f"    Sample cell: world({cx:.1f}, {cy:.1f}) ✓")
    else:
        print("    (No dump cells yet)")
    
    # 7. Summary
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print(f"Active trucks: {len(trucks)}")
    print(f"Total dumps: {state['metrics']['total_dumps']}")
    print(f"Packing density: {state['metrics']['packing_density']*100:.1f}%")
    print(f"Fleet utilization: {state['metrics']['fleet_utilization']*100:.1f}%")

if __name__ == '__main__':
    try:
        test_complete_flow()
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        exit(1)
