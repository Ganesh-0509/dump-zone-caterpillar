#!/usr/bin/env python3
"""Test frontend coordinate transformation pipeline."""

import requests
import time

BASE_URL = "http://localhost:5000"

def test_coordinate_pipeline():
    """Test the complete coordinate pipeline."""
    print("Starting coordinate pipeline test...")
    
    # 1. Initialize
    print("\n1. POST /api/init")
    resp = requests.post(f"{BASE_URL}/api/init")
    result = resp.json()
    print(f"   Status: {result.get('status')}")
    
    # 2. Get metadata
    print("\n2. GET /api/metadata")
    resp = requests.get(f"{BASE_URL}/api/metadata")
    meta = resp.json()
    print(f"   Status: {meta.get('status')}")
    bounds = meta.get('bounds', {})
    print(f"   Bounds: ({bounds.get('min_x')}, {bounds.get('min_y')}) to ({bounds.get('max_x')}, {bounds.get('max_y')})")
    print(f"   Zones: {meta.get('zones')}")
    
    # 3. Step a few times to let trucks spawn
    print("\n3. Running 10 simulation steps...")
    for i in range(10):
        requests.post(f"{BASE_URL}/api/step")
    
    # 4. Get state with truck positions
    print("\n4. GET /api/state")
    resp = requests.get(f"{BASE_URL}/api/state")
    state = resp.json()
    
    if state.get('trucks'):
        truck = state['trucks'][0]
        x, y = truck.get('x'), truck.get('y')
        print(f"   First truck position: ({x}, {y})")
        
        # Simulate frontend coordinate transform
        print("\n5. Frontend coordinate transform:")
        canvas_width = 704  # Typical browser canvas width
        canvas_height = 688  # Typical browser canvas height
        
        b = bounds
        width_range = max(b['max_x'] - b['min_x'], 1e-9)
        height_range = max(b['max_y'] - b['min_y'], 1e-9)
        
        scale_x = canvas_width / width_range
        scale_y = canvas_height / height_range
        scale = min(scale_x, scale_y) * 0.95
        
        offset_x = (canvas_width - width_range * scale) / 2
        offset_y = (canvas_height - height_range * scale) / 2
        
        print(f"   Canvas: {canvas_width}x{canvas_height}")
        print(f"   Width/Height range: {width_range}, {height_range}")
        print(f"   Scale X/Y: {scale_x:.2f}, {scale_y:.2f}")
        print(f"   Final scale: {scale:.2f}")
        print(f"   Offsets: X={offset_x:.1f}, Y={offset_y:.1f}")
        
        # Transform truck position
        screen_x = offset_x + (x - b['min_x']) * scale
        screen_y = offset_y + (y - b['min_y']) * scale
        
        print(f"   Truck world ({x}, {y}) -> screen ({screen_x:.1f}, {screen_y:.1f})")
        
        # Check if transforms seem reasonable
        if 0 <= screen_x <= canvas_width and 0 <= screen_y <= canvas_height:
            print("   ✓ Screen coordinates are within canvas bounds")
        else:
            print(f"   ✗ WARNING: Screen coordinates outside canvas!")
    else:
        print("   No trucks spawned yet")

if __name__ == '__main__':
    test_coordinate_pipeline()
