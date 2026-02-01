"""
Orbital Propagator Module

Wraps SGP4 propagation to generate ECI position vectors over time.

Why SGP4?
- SGP4 (Simplified General Perturbations 4) is the standard propagator for TLE data
- It includes perturbations for Earth oblateness (J2), atmospheric drag, and solar/lunar effects
- It is validated against decades of operational use by NORAD/Space Command
- TLE elements are specifically fitted for SGP4; using a different propagator would be incorrect

Why ECI (Earth-Centered Inertial)?
- ECI is a non-rotating reference frame with origin at Earth's center
- X-axis points toward vernal equinox, Z-axis toward celestial north pole
- Avoids complexity of accounting for Earth's rotation in distance calculations
- Natural frame for orbital mechanics computations
"""

from datetime import datetime, timedelta
from sgp4.api import jday


# Constants
SECONDS_PER_DAY = 86400
DEFAULT_TIME_STEP_SECONDS = 30
DEFAULT_TIME_HORIZON_HOURS = 24
KM_TO_METERS = 1000.0


def propagate_orbit(satellite_obj: dict, 
                    start_time: datetime,
                    duration_hours: float = DEFAULT_TIME_HORIZON_HOURS,
                    time_step_seconds: float = DEFAULT_TIME_STEP_SECONDS) -> list:
    """
    Propagate a satellite's orbit and return ECI positions.
    
    Args:
        satellite_obj: Parsed TLE dictionary from tle_parser
        start_time: UTC datetime to start propagation
        duration_hours: How many hours to propagate (default: 24)
        time_step_seconds: Time between position samples (default: 30)
    
    Returns:
        List of dictionaries containing:
        - timestamp: ISO format UTC time
        - position: [x, y, z] in meters (ECI frame)
        - valid: Boolean indicating if propagation was successful
    """
    satellite = satellite_obj['satellite']
    
    positions = []
    current_time = start_time
    end_time = start_time + timedelta(hours=duration_hours)
    
    while current_time <= end_time:
        # Convert datetime to Julian date for SGP4
        jd, fr = jday(
            current_time.year,
            current_time.month,
            current_time.day,
            current_time.hour,
            current_time.minute,
            current_time.second + current_time.microsecond / 1e6
        )
        
        # Propagate using SGP4
        # Returns error code, position (km), velocity (km/s)
        error, position_km, velocity_km_s = satellite.sgp4(jd, fr)
        
        if error == 0:
            # Convert km to meters
            position_m = [
                position_km[0] * KM_TO_METERS,
                position_km[1] * KM_TO_METERS,
                position_km[2] * KM_TO_METERS
            ]
            positions.append({
                'timestamp': current_time.isoformat() + 'Z',
                'position': position_m,
                'valid': True
            })
        else:
            # SGP4 error - position may be invalid (e.g., decayed orbit)
            positions.append({
                'timestamp': current_time.isoformat() + 'Z',
                'position': [0.0, 0.0, 0.0],
                'valid': False,
                'error_code': error
            })
        
        current_time += timedelta(seconds=time_step_seconds)
    
    return positions


def get_average_orbital_radius(satellite_obj: dict, start_time: datetime) -> float:
    """
    Compute approximate average orbital radius for pre-filtering.
    
    This is used as a coarse filter to skip debris objects that are
    clearly in different orbital regimes (e.g., LEO satellite vs GEO debris).
    
    Args:
        satellite_obj: Parsed TLE dictionary
        start_time: Reference time for calculation
    
    Returns:
        Average orbital radius in meters from Earth center
    """
    satellite = satellite_obj['satellite']
    
    # Sample a few points to get average radius
    sample_times = [start_time + timedelta(minutes=i*30) for i in range(4)]
    radii = []
    
    for t in sample_times:
        jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second)
        error, position_km, _ = satellite.sgp4(jd, fr)
        
        if error == 0:
            # Compute distance from Earth center
            r = (position_km[0]**2 + position_km[1]**2 + position_km[2]**2) ** 0.5
            radii.append(r * KM_TO_METERS)
    
    if radii:
        return sum(radii) / len(radii)
    else:
        return 0.0


def propagate_batch(objects: list, 
                    start_time: datetime,
                    duration_hours: float = DEFAULT_TIME_HORIZON_HOURS,
                    time_step_seconds: float = DEFAULT_TIME_STEP_SECONDS) -> dict:
    """
    Propagate multiple objects simultaneously.
    
    All objects are propagated at identical timestamps for consistent
    distance calculations.
    
    Args:
        objects: List of parsed TLE dictionaries
        start_time: UTC datetime to start propagation
        duration_hours: How many hours to propagate
        time_step_seconds: Time between position samples
    
    Returns:
        Dictionary mapping object names to their position histories
    """
    results = {}
    
    for obj in objects:
        name = obj['name']
        positions = propagate_orbit(obj, start_time, duration_hours, time_step_seconds)
        results[name] = {
            'catalog_number': obj['catalog_number'],
            'positions': positions
        }
    
    return results
