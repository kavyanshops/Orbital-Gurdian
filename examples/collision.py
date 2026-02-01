#!/usr/bin/env python3
"""
Example: Run collision simulation with visualization
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from space_navigator.api.environment import SpaceEnvironment
from space_navigator.simulator.simulator import Simulator, run_simulation


def main():
    parser = argparse.ArgumentParser(
        description="Run collision simulation"
    )
    parser.add_argument(
        "--env", "-e",
        type=str,
        required=True,
        help="Path to environment JSON"
    )
    parser.add_argument(
        "--maneuvers", "-m",
        type=str,
        default=None,
        help="Path to maneuvers CSV (optional)"
    )
    parser.add_argument(
        "--visualize", "-v",
        action="store_true",
        default=True,
        help="Show visualization"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save figure to path"
    )
    
    args = parser.parse_args()
    
    print(f"Loading environment: {args.env}")
    env = SpaceEnvironment.from_json(args.env)
    
    maneuvers = None
    if args.maneuvers:
        print(f"Loading maneuvers: {args.maneuvers}")
        maneuvers = Simulator.load_maneuvers(args.maneuvers)
    
    print(f"\nRunning simulation...")
    print(f"  Satellite: {env.satellite.name}")
    print(f"  Debris: {len(env.debris)}")
    print(f"  Time span: {(env.end_epoch - env.start_epoch) * 24 * 60:.1f} minutes")
    
    sim = Simulator(env, maneuvers)
    summary = sim.run()
    
    print(f"\n{'='*50}")
    print("SIMULATION RESULTS")
    print(f"{'='*50}")
    print(f"  Total steps: {summary['total_steps']}")
    print(f"  Max collision probability: {summary['max_collision_probability']:.2e}")
    print(f"  Cumulative collision probability: {summary['cumulative_collision_probability']:.2e}")
    print(f"  Fuel consumed: {summary['fuel_consumed']:.2f} m/s")
    print(f"  Fuel remaining: {summary['fuel_remaining']:.2f} m/s")
    print(f"  Maneuvers applied: {summary['maneuvers_applied']}")
    print(f"  Threshold exceeded: {summary['threshold_exceeded']}")
    print(f"  SUCCESS: {summary['success']}")
    print(f"{'='*50}")
    
    if args.visualize:
        sim.visualize_results(save_path=args.output)


if __name__ == "__main__":
    main()
