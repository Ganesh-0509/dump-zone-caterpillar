#!/usr/bin/env python
"""Verify frontend setup is correct."""

import sys
from pathlib import Path

def check_frontend():
    """Verify all frontend components are in place."""
    print("=" * 70)
    print("FRONTEND SETUP VERIFICATION")
    print("=" * 70)
    
    project_root = Path(__file__).resolve().parent
    checks_passed = 0
    checks_total = 0
    
    # Check Flask
    checks_total += 1
    try:
        import flask
        print(f"✓ Flask {flask.__version__} installed")
        checks_passed += 1
    except ImportError:
        print("✗ Flask not installed - run: pip install flask flask-cors")
    
    # Check CORS
    checks_total += 1
    try:
        import flask_cors
        print(f"✓ Flask-CORS installed")
        checks_passed += 1
    except ImportError:
        print("✗ Flask-CORS not installed - run: pip install flask-cors")
    
    # Check templates exist
    checks_total += 1
    template_path = project_root / "templates" / "dashboard.html"
    if template_path.exists():
        print(f"✓ Dashboard template found: {template_path}")
        checks_passed += 1
    else:
        print(f"✗ Dashboard template missing: {template_path}")
    
    # Check app.py exists
    checks_total += 1
    app_path = project_root / "app.py"
    if app_path.exists():
        print(f"✓ Flask app found: {app_path}")
        checks_passed += 1
    else:
        print(f"✗ Flask app missing: {app_path}")
    
    # Check simulation engine
    checks_total += 1
    sim_path = project_root / "simulation" / "simulation_engine.py"
    if sim_path.exists():
        print(f"✓ Simulation engine found")
        checks_passed += 1
    else:
        print(f"✗ Simulation engine missing")
    
    # Summary
    print("\n" + "=" * 70)
    print(f"VERIFICATION: {checks_passed}/{checks_total} checks passed")
    print("=" * 70)
    
    if checks_passed == checks_total:
        print("\n✅ Frontend setup is complete!")
        print("\n▶ To start the frontend, run:")
        print("   python run_frontend.py")
        print("\n📍 The server will open at http://localhost:5000")
        return 0
    else:
        print(f"\n❌ {checks_total - checks_passed} check(s) failed")
        print("Please fix the above issues and try again.")
        return 1

if __name__ == '__main__':
    sys.exit(check_frontend())
