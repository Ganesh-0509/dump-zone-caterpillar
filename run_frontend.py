#!/usr/bin/env python
"""Simple launcher script for the dump simulator frontend."""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def main():
    """Start the Flask server and open browser."""
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return 1
    
    project_root = Path(__file__).resolve().parent
    
    print("=" * 70)
    print("🚜 Caterpillar Dump Simulator - Frontend")
    print("=" * 70)
    
    # Check if Flask is installed
    try:
        import flask
        print("✓ Flask is installed")
    except ImportError:
        print("❌ Flask not found. Installing dependencies...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", 
            str(project_root / "requirements-frontend.txt")
        ])
    
    print("\n🌐 Starting server on http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        # Start Flask server
        from app import app
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(2)
            print("🌍 Opening browser...")
            webbrowser.open('http://localhost:5000')
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        app.run(debug=False, host='localhost', port=5000, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
