"""
Conjunction Screening Module

Computes closest approach between a satellite and debris objects.

Algorithm:
1. Pre-filter: Skip debris with orbital radius differing by >50km (coarse filter)
2. For each timestep, compute Euclidean distance in ECI frame
3. Track minimum distance and time of closest approach
4. Flag warnings for distances < 10,000 meters

Assumptions and Limitations:
- This is a screening tool, not operational collision avoidance
- No covariance/uncertainty propagation
- No maneuver optimization
- Assumes point masses (no attitude or physical dimensions)
- Time resolution limited by step size (may miss brief close approaches)
"""

import math
from datetime import datetime
from typing import Optional

from .propagator import propagate_orbit, get_average_orbital_radius


# Constants
ALERT_THRESHOLD_METERS = 10000.0  # 10 km
ORBITAL_RADIUS_FILTER_METERS = 50000.0  # 50 km pre-filter
METERS_TO_KM = 0.001


def generate_maneuver_recommendation(status: str, min_distance: float, 
                                      closest_time: str, start_time: datetime) -> dict:
    """
    Generate maneuver/dodge recommendations based on conjunction data.
    
    Args:
        status: 'WARNING' or 'SAFE'
        min_distance: Minimum distance in meters
        closest_time: ISO timestamp of closest approach
        start_time: Analysis start time
        
    Returns:
        Dictionary with recommendation details
    """
    if status != 'WARNING' or not closest_time:
        return None
    
    from datetime import timedelta
    from dateutil import parser
    
    try:
        # Parse closest approach time
        tca = parser.parse(closest_time.replace('Z', '+00:00'))
        time_to_tca = tca - start_time
        hours_to_tca = time_to_tca.total_seconds() / 3600
        
        # Determine urgency based on time to TCA
        if hours_to_tca < 2:
            urgency = 'CRITICAL'
            urgency_color = '#ff4444'
            action = 'IMMEDIATE MANEUVER REQUIRED'
        elif hours_to_tca < 6:
            urgency = 'HIGH'
            urgency_color = '#ff8800'
            action = 'Plan maneuver within 1 hour'
        elif hours_to_tca < 12:
            urgency = 'MEDIUM'
            urgency_color = '#ffcc00'
            action = 'Schedule maneuver assessment'
        else:
            urgency = 'LOW'
            urgency_color = '#88cc00'
            action = 'Continue monitoring, plan ahead'
        
        # Calculate recommended maneuver timing (2 hours before TCA is optimal)
        maneuver_time = tca - timedelta(hours=2)
        if maneuver_time < start_time:
            maneuver_time = start_time + timedelta(minutes=30)
        
        # Estimate delta-V (rough approximation for educational purposes)
        # Actual delta-V calculation requires detailed orbital mechanics
        miss_distance_km = min_distance * METERS_TO_KM
        estimated_delta_v = max(0.1, 10 / miss_distance_km) if miss_distance_km > 0 else 10.0
        estimated_delta_v = min(estimated_delta_v, 10.0)  # Cap at 10 m/s
        
        return {
            'urgency': urgency,
            'urgency_color': urgency_color,
            'action': action,
            'hours_to_tca': round(hours_to_tca, 1),
            'recommended_maneuver_time': maneuver_time.isoformat() + 'Z',
            'estimated_delta_v_ms': round(estimated_delta_v, 2),
            'recommendation': f'Execute radial or along-track maneuver by {maneuver_time.strftime("%H:%M UTC")} to increase miss distance'
        }
    except Exception:
        return {
            'urgency': 'UNKNOWN',
            'action': 'Unable to calculate - review manually'
        }


def compute_distance(pos1: list, pos2: list) -> float:
    """
    Compute Euclidean distance between two ECI positions.
    
    Args:
        pos1: [x, y, z] position in meters
        pos2: [x, y, z] position in meters
    
    Returns:
        Distance in meters
    """
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def screen_debris(satellite_obj: dict, 
                  debris_list: list,
                  start_time: datetime,
                  duration_hours: float = 24.0,
                  time_step_seconds: float = 30.0,
                  use_prefilter: bool = True) -> dict:
    """
    Screen multiple debris objects against a satellite.
    
    Args:
        satellite_obj: Parsed TLE dictionary for the primary satellite
        debris_list: List of parsed TLE dictionaries for debris
        start_time: UTC datetime to start screening
        duration_hours: Time horizon for analysis
        time_step_seconds: Time resolution
        use_prefilter: Whether to apply 50km orbital radius filter
    
    Returns:
        Dictionary containing:
        - overall_status: 'SAFE' or 'WARNINGS_PRESENT'
        - analysis_start: ISO timestamp
        - analysis_end: ISO timestamp
        - time_step_seconds: Resolution used
        - total_debris_screened: Number of debris analyzed
        - debris_filtered: Number skipped by pre-filter
        - results: List of per-debris screening results
    """
    # Get satellite orbital radius for pre-filtering
    sat_radius = get_average_orbital_radius(satellite_obj, start_time)
    
    # Propagate satellite orbit
    sat_positions = propagate_orbit(
        satellite_obj, start_time, duration_hours, time_step_seconds
    )
    
    results = []
    filtered_count = 0
    warnings_present = False
    
    for debris in debris_list:
        # Pre-filter by orbital radius
        if use_prefilter:
            debris_radius = get_average_orbital_radius(debris, start_time)
            radius_diff = abs(sat_radius - debris_radius)
            
            if radius_diff > ORBITAL_RADIUS_FILTER_METERS:
                filtered_count += 1
                results.append({
                    'debris_id': debris['name'],
                    'catalog_number': debris['catalog_number'],
                    'status': 'FILTERED',
                    'reason': f'Orbital radius difference: {radius_diff * METERS_TO_KM:.1f} km',
                    'min_distance_km': None,
                    'closest_approach_time': None
                })
                continue
        
        # Propagate debris orbit
        debris_positions = propagate_orbit(
            debris, start_time, duration_hours, time_step_seconds
        )
        
        # Find minimum distance
        min_distance = float('inf')
        closest_time: Optional[str] = None
        
        for sat_pos, deb_pos in zip(sat_positions, debris_positions):
            # Skip invalid positions
            if not sat_pos['valid'] or not deb_pos['valid']:
                continue
            
            distance = compute_distance(sat_pos['position'], deb_pos['position'])
            
            if distance < min_distance:
                min_distance = distance
                closest_time = sat_pos['timestamp']
        
        # Determine status
        if min_distance < ALERT_THRESHOLD_METERS:
            status = 'WARNING'
            warnings_present = True
        else:
            status = 'SAFE'
        
        results.append({
            'debris_id': debris['name'],
            'catalog_number': debris['catalog_number'],
            'status': status,
            'min_distance_km': round(min_distance * METERS_TO_KM, 3),
            'min_distance_m': round(min_distance, 1),
            'closest_approach_time': closest_time,
            'maneuver_recommendation': generate_maneuver_recommendation(status, min_distance, closest_time, start_time) if status == 'WARNING' else None
        })
    
    # Sort by minimum distance (warnings first, then by distance)
    def sort_key(item):
        if item['status'] == 'FILTERED':
            return (2, float('inf'))
        elif item['status'] == 'WARNING':
            return (0, item['min_distance_km'])
        else:
            return (1, item['min_distance_km'])
    
    results.sort(key=sort_key)
    
    # Calculate analysis time range
    from datetime import timedelta
    end_time = start_time + timedelta(hours=duration_hours)
    
    return {
        'overall_status': 'WARNINGS_PRESENT' if warnings_present else 'SAFE',
        'satellite_name': satellite_obj['name'],
        'satellite_catalog_number': satellite_obj['catalog_number'],
        'analysis_start': start_time.isoformat() + 'Z',
        'analysis_end': end_time.isoformat() + 'Z',
        'time_step_seconds': time_step_seconds,
        'total_debris_screened': len(debris_list),
        'debris_filtered': filtered_count,
        'debris_analyzed': len(debris_list) - filtered_count,
        'warnings_count': sum(1 for r in results if r['status'] == 'WARNING'),
        'results': results
    }
