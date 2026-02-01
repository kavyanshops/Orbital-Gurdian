#!/usr/bin/env python3
"""
Collision Scenario Generator

Generates random collision scenarios for training and testing.
"""

import argparse
import json
import numpy as np
import math
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from space_navigator.api.environment import SpaceEnvironment, Satellite, Debris
from space_navigator.api.orbital_mechanics import OrbitalElements, EARTH_RADIUS


def generate_random_elements(
    altitude_min: float = 300e3,
    altitude_max: float = 800e3,
    eccentricity_max: float = 0.01,
    inclination_range: tuple = (0.5, 1.5),  # radians (~30-85 deg)
    epoch: float = 6601.0
) -> OrbitalElements:
    """Generate random LEO orbital elements."""
    a = EARTH_RADIUS + np.random.uniform(altitude_min, altitude_max)
    e = np.random.uniform(0, eccentricity_max)
    i = np.random.uniform(*inclination_range)
    raan = np.random.uniform(0, 2 * math.pi)
    omega = np.random.uniform(0, 2 * math.pi)
    M = np.random.uniform(0, 2 * math.pi)
    
    return OrbitalElements(a=a, e=e, i=i, raan=raan, omega=omega, M=M, epoch=epoch)


def generate_nearby_elements(
    reference: OrbitalElements,
    delta_altitude: float = 50e3,
    delta_inclination: float = 0.1,
    delta_raan: float = 0.2
) -> OrbitalElements:
    """Generate elements near a reference orbit (for potential collision)."""
    a = reference.a + np.random.uniform(-delta_altitude, delta_altitude)
    e = np.clip(reference.e + np.random.uniform(-0.005, 0.005), 0, 0.1)
    i = reference.i + np.random.uniform(-delta_inclination, delta_inclination)
    raan = reference.raan + np.random.uniform(-delta_raan, delta_raan)
    omega = np.random.uniform(0, 2 * math.pi)
    M = np.random.uniform(0, 2 * math.pi)
    
    return OrbitalElements(a=a, e=e, i=i, raan=raan, omega=omega, M=M, epoch=reference.epoch)


def generate_collision_scenario(
    n_debris: int = 5,
    start_epoch: float = 6601.0,
    end_epoch: float = 6601.1,
    near_collision_fraction: float = 0.4,
    seed: int = None
) -> SpaceEnvironment:
    """
    Generate a collision scenario.
    
    Args:
        n_debris: Number of debris objects
        start_epoch: Start epoch [MJD2000]
        end_epoch: End epoch [MJD2000]
        near_collision_fraction: Fraction of debris near satellite orbit
        seed: Random seed
        
    Returns:
        SpaceEnvironment
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Generate satellite
    sat_elements = generate_random_elements(epoch=start_epoch)
    satellite = Satellite(
        name="PROTECTED-SAT",
        orbital_elements=sat_elements,
        radius=5.0,
        mass=500,
        fuel=50
    )
    
    # Generate debris
    n_near = int(n_debris * near_collision_fraction)
    debris_list = []
    
    for i in range(n_debris):
        if i < n_near:
            # Near the satellite (potential collision)
            elements = generate_nearby_elements(sat_elements)
        else:
            # Random orbit
            elements = generate_random_elements(epoch=start_epoch)
        
        debris_list.append(Debris(
            name=f"DEBRIS-{i+1:03d}",
            orbital_elements=elements,
            radius=np.random.uniform(0.05, 0.5)
        ))
    
    return SpaceEnvironment(
        satellite=satellite,
        debris=debris_list,
        start_epoch=start_epoch,
        end_epoch=end_epoch
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate random collision scenarios"
    )
    parser.add_argument(
        "--save_path", "-o",
        type=str,
        default="data/environments/scenario.json",
        help="Path to save environment JSON"
    )
    parser.add_argument(
        "--n_debris", "-n",
        type=int,
        default=5,
        help="Number of debris objects"
    )
    parser.add_argument(
        "--start_epoch",
        type=float,
        default=6601.0,
        help="Start epoch (MJD2000)"
    )
    parser.add_argument(
        "--end_epoch",
        type=float,
        default=6601.1,
        help="End epoch (MJD2000)"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed"
    )
    parser.add_argument(
        "--near_fraction",
        type=float,
        default=0.4,
        help="Fraction of debris near satellite orbit"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.save_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Generate scenario
    print(f"Generating scenario with {args.n_debris} debris objects...")
    env = generate_collision_scenario(
        n_debris=args.n_debris,
        start_epoch=args.start_epoch,
        end_epoch=args.end_epoch,
        near_collision_fraction=args.near_fraction,
        seed=args.seed
    )
    
    # Save
    env.to_json(args.save_path)
    print(f"Saved to: {args.save_path}")
    
    # Print summary
    print(f"\nScenario Summary:")
    print(f"  Satellite: {env.satellite.name}")
    print(f"  Altitude: {(env.satellite.orbital_elements.a - EARTH_RADIUS)/1000:.0f} km")
    print(f"  Debris: {len(env.debris)}")
    print(f"  Time span: {(args.end_epoch - args.start_epoch) * 24 * 60:.1f} minutes")


if __name__ == "__main__":
    main()
