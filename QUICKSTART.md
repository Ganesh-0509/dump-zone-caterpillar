# 🚜 Dump Simulator - Quick Start Guide

## Installation & Setup (2 minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements-frontend.txt
```

### Step 2: Verify Setup
```bash
python verify_frontend.py
```

Expected output: ✅ Frontend setup is complete!

### Step 3: Launch the Frontend
```bash
python run_frontend.py
```

The browser will automatically open to **http://localhost:5000**

---

## Using the Dashboard

### 🎮 Basic Controls

| Button | Action |
|--------|--------|
| **Initialize** | Create a fresh simulation with 5 zones and multiple trucks |
| **Play** | Start running the simulation continuously |
| **Pause** | Stop simulation (can resume with Play) |
| **Step** | Advance exactly 1 simulation step |
| **Reset** | Clear everything and start over |

### 📊 Reading the Dashboard

**Left Canvas:**
- **🟢 Green circles** = Trucks moving to zones
- **🟠 Orange circles** = Trucks dumping material  
- **🔵 Blue circles** = Trucks returning to entrance
- **🟫 Brown squares** = Material piles
- **Yellow lines** = Zone boundaries

**Right Sidebar:**
- **Metrics Panel** - Real-time KPIs
- **Fleet Status** - Active trucks and zones
- **Speed Control** - 1x to 100x simulation speed
- **Legend** - Visual reference guide

---

## Example Workflow

### Scenario: Watch First 100 Steps

1. Click **Initialize** (wait 2 seconds for load)
2. Set speed slider to **10x**
3. Click **Play** (let it run for ~10 seconds)
4. Click **Pause**
5. Observe metrics:
   - How many trucks spawned?
   - What's the packing density?
   - Where are the dump piles?

### Scenario: Manual Step-by-Step Inspection

1. Click **Initialize**
2. Repeatedly click **Step** (advances 1 step at a time)
3. Watch trucks spawn and move
4. See dump events happen
5. Monitor metrics updating

### Scenario: Performance Testing

1. Click **Initialize**
2. Set speed slider to **100x** (fastest)
3. Click **Play**
4. Let run for 30 seconds
5. Click **Pause**
6. Check final metrics:
   - Total dumps completed
   - Total trucks processed
   - System performance

---

## Key Features Demonstrated

### ✅ Deadlock Prevention
- Trucks automatically replan if stuck >20 steps
- No circular wait patterns
- Watch trucks navigate around blocked areas

### ✅ Slope-Aware Dumping  
- Piles maintain stable slopes (max 0.6 grade)
- Material spreads across zone rather than stacking
- Prevents unstable pile formation

### ✅ Intelligent Truck Distribution
- Trucks assigned to different dump zones
- Each truck picks best dump location
- Avoids collision hotspots

### ✅ Real-time Metrics
- **Packing Density** - How full is the dump zone?
- **Fleet Utilization** - % of trucks working
- **Pile Metrics** - Height, slope, layer growth
- **Throughput** - Dumps per timekeeper

---

## Performance Expectations

### Typical Simulation (60 seconds runtime)
- **Trucks Spawned:** 25-35
- **Total Dumps:** 25-35
- **Zones Used:** 3-5  
- **Avg Cycle Time:** 2-3 minutes per truck
- **Packing Density:** 0.1-0.3%

### Speed Settings
| Speed | Best For | Steps/sec |
|-------|----------|-----------|
| 1x | Visual inspection | 20 |
| 10x | Balanced view | 200 |
| 50x | Testing | 1000 |
| 100x | Maximum speed | 2000+ |

---

## Troubleshooting

### Issue: Browser won't open automatically
**Solution:** Manually visit http://localhost:5000

### Issue: "Port 5000 already in use"
**Solution:** Edit `app.py` line at bottom:
```python
app.run(debug=False, host='localhost', port=5001)
```

### Issue: Dashboard loads but no interaction
**Solution:** 
1. Press F12 to open browser console
2. Check for error messages
3. Click "Initialize" to start fresh

### Issue: Simulation very slow
**Solution:**
1. Lower speed slider to 10x
2. Close other browser tabs
3. Restart the browser

### Issue: Trucks not moving
**Solution:**
1. Make sure you clicked "Initialize" first
2. Then click "Play"
3. Check metrics panel for active trucks count

---

## API Endpoints Reference

All endpoints return JSON. Access via:
```
http://localhost:5000/api/[endpoint]
```

### GET `/api/metadata`
Returns simulation bounds and configuration:
```json
{
  "bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100},
  "grid": {"width": 200, "height": 200, "cell_size": 0.5},
  "zones": 5
}
```

### POST `/api/init`
Initialize new simulation

### POST `/api/step`  
Execute 1 simulation step

### GET `/api/state`
Current simulation state with all trucks, dumps, metrics

### POST `/api/reset`
Clear and restart simulation

---

## Advanced Tips

### Monitor System Performance
Check metrics panel for:
- **Cycle Time** - How long each truck takes
- **Throughput** - Dumps per step
- **Utilization** - % trucks active

### Identify Bottlenecks
- Look for clusters of trucks at one location
- Check if dump zones are balanced
- Monitor slope stability

### Test New Configurations
Edit `app.py`:
```python
zone_config = ZoneGenerationConfig(zone_count=5, random_seed=42)
```
Change `zone_count` (3-10) or `random_seed` (0-100)

---

## System Architecture

```
┌─────────────────────────────────────────┐
│  Browser (HTML/CSS/JavaScript)          │
│  - Canvas visualization                 │
│  - Metrics dashboard                    │
│  - Simulation controls                  │
└────────────┬────────────────────────────┘
             │ HTTP/JSON API
┌────────────▼────────────────────────────┐
│  Flask Backend (app.py)                 │
│  - REST API endpoints                   │
│  - State management                     │
│  - Step computation                     │
└────────────┬────────────────────────────┘
             │ Python objects
┌────────────▼────────────────────────────┐
│  SimulationEngine                       │
│  - DeadlockManager                      │
│  - SlopeValidator                       │
│  - TrafficManager                       │
│  - AnalyticsManager                     │
│  - Truck agents & zones                 │
└─────────────────────────────────────────┘
```

---

## What's Next?

After running the simulator:

1. **Experiment with zones**
   - Change zone count in app.py
   - See how it affects truck distribution

2. **Analyze metrics** 
   - Export step-by-step data
   - Plot trends in spreadsheet

3. **Optimize configuration**
   - Adjust truck spawn rates
   - Modify zone sizes
   - Test different payloads

4. **Scale testing**
   - Run longer simulations (1000+ steps)
   - Monitor memory usage
   - Benchmark performance

---

## File Structure

```
dump-zone-simulator/
├── app.py                    ← Flask backend
├── requirements-frontend.txt ← Dependencies  
├── run_frontend.py          ← Simple launcher
├── verify_frontend.py       ← Setup checker
├── start_frontend.bat       ← Windows batch file
├── templates/
│   └── dashboard.html       ← Web interface
├── simulation/
│   ├── simulation_engine.py
│   ├── truck_agent.py
│   └── truck_generator.py
├── planning/
│   ├── deadlock_manager.py
│   ├── slope_validator.py
│   ├── traffic_manager.py
│   └── analytics_manager.py
└── data/
    └── dump_polygon.json    ← Zone definition
```

---

## Support & Troubleshooting

1. **Check browser console** (F12)
2. **Review FRONTEND_README.md** for detailed docs
3. **Run verify_frontend.py** to diagnose setup issues
4. **Check server logs** in terminal

---

**Enjoy exploring the Caterpillar Optimal Dump Packing System! 🎉**
