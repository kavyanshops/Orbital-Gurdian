# Collision Avoidance Alert System

**Space Hackathon 2026 - Conjunction Screening System**

> ⚠️ **Disclaimer**: This project performs conjunction screening using SGP4-propagated TLE data. It is intended for educational demonstration and does not represent operational collision avoidance.

## Overview

A physically correct conjunction screening system that:
- Loads satellite orbits from TLE (Two-Line Element) data
- Loads space debris objects from TLE data
- Propagates all objects forward in time using SGP4
- Computes closest approach distances in ECI frame
- Triggers alerts when debris comes within 10 km threshold

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/ks/Desktop/SAST\ HACKTHONE
pip install -r requirements.txt
```

### 2. Start Backend Server

```bash
python -m backend.app
```

The server runs on `http://localhost:5000`.

### 3. Open Frontend

Open `frontend/index.html` in your browser.

### 4. Run Analysis

1. Load sample TLEs (or enter your own)
2. Configure analysis parameters
3. Click "Run Analysis"
4. View results table and warnings

## Project Structure

```
SAST HACKTHONE/
├── backend/
│   ├── __init__.py
│   ├── tle_parser.py        # TLE parsing utilities
│   ├── propagator.py        # SGP4 orbit propagation
│   ├── conjunction_screening.py  # Distance calculations
│   └── app.py               # Flask API server
├── frontend/
│   ├── index.html           # Web interface
│   ├── styles.css           # Styling
│   └── app.js               # Frontend logic
├── requirements.txt
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Run conjunction screening |
| `/health` | GET | Health check |
| `/sample-data` | GET | Get sample TLE data |

### POST /analyze

Request body:
```json
{
    "satellite_tle": "NAME\n1 ...\n2 ...",
    "debris_tles": "NAME1\n1 ...\n2 ...\nNAME2\n1 ...\n2 ...",
    "duration_hours": 24,
    "time_step_seconds": 30,
    "use_prefilter": true
}
```

## Technical Explanation

### Why SGP4?

SGP4 (Simplified General Perturbations 4) is the standard propagator for TLE data. Key points:
- TLE elements are specifically fitted for SGP4 propagation
- Includes perturbations for Earth's oblateness (J2), atmospheric drag, and solar/lunar effects
- Validated against decades of operational use by NORAD/Space Command
- Using a different propagator with TLE data would produce incorrect results

### Why ECI (Earth-Centered Inertial)?

- Origin at Earth's center
- X-axis toward vernal equinox, Z-axis toward celestial north pole
- Non-rotating frame simplifies distance calculations
- Natural coordinate system for orbital mechanics

### Assumptions

- All objects treated as point masses
- TLE data assumed current and accurate
- Earth modeled with SGP4 perturbations only
- Time resolution limited by step size (30 seconds default)

### Limitations

- No covariance/uncertainty propagation
- No probability of collision calculation
- No maneuver optimization
- Not suitable for operational decisions

## Configuration

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Duration | 24 hours | 1-168 hours | Analysis time window |
| Time Step | 30 seconds | 1-3600 seconds | Position sample interval |
| Pre-filter | Enabled | On/Off | Skip debris with orbital radius >50km different |
| Alert Threshold | 10 km | Fixed | Warning trigger distance |

## Validation

Run tests to verify correctness:

```bash
# Unit tests
python -m pytest tests/ -v

# Manual validation
# 1. Distances should never be negative
# 2. Results should be identical across reruns
# 3. Removing debris should reduce warnings
```

## Data Sources

For real TLE data:
- [CelesTrak](https://celestrak.org/)
- [Space-Track](https://www.space-track.org/)

## License

Educational use only. Not for operational collision avoidance.
