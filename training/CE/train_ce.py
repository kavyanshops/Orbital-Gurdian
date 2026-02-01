#!/usr/bin/env python3
"""
Cross-Entropy Method Training Script

Train a CE agent on a collision scenario.
"""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from space_navigator.api.environment import SpaceEnvironment
from space_navigator.models.cross_entropy import CrossEntropyAgent
from space_navigator.simulator.simulator import Simulator


def main():
    parser = argparse.ArgumentParser(
        description="Train Cross-Entropy agent"
    )
    parser.add_argument(
        "--env", "-e",
        type=str,
        required=True,
        help="Path to environment JSON"
    )
    parser.add_argument(
        "--save_path", "-o",
        type=str,
        default="results/maneuvers_ce.csv",
        help="Path to save maneuvers"
    )
    parser.add_argument(
        "--n_iterations", "-i",
        type=int,
        default=100,
        help="Number of iterations"
    )
    parser.add_argument(
        "--population_size", "-p",
        type=int,
        default=50,
        help="Population size"
    )
    parser.add_argument(
        "--elite_fraction",
        type=float,
        default=0.2,
        help="Elite fraction"
    )
    parser.add_argument(
        "--n_maneuvers", "-m",
        type=int,
        default=3,
        help="Number of maneuvers to optimize"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed"
    )
    parser.add_argument(
        "--visualize", "-v",
        action="store_true",
        help="Visualize results"
    )
    
    args = parser.parse_args()
    
    # Load environment
    print(f"Loading environment: {args.env}")
    env = SpaceEnvironment.from_json(args.env)
    
    # Create agent
    agent = CrossEntropyAgent(
        environment=env,
        n_maneuvers=args.n_maneuvers,
        population_size=args.population_size,
        elite_fraction=args.elite_fraction,
        n_iterations=args.n_iterations,
        seed=args.seed
    )
    
    # Train
    print(f"Training CE agent...")
    print(f"  Population: {args.population_size}")
    print(f"  Elite fraction: {args.elite_fraction}")
    print(f"  Iterations: {args.n_iterations}")
    print()
    
    maneuvers = agent.optimize(verbose=True)
    
    # Save maneuvers
    Path(args.save_path).parent.mkdir(parents=True, exist_ok=True)
    agent.save_maneuvers(args.save_path)
    print(f"\nManeuvers saved to: {args.save_path}")
    
    # Evaluate final result
    print("\nFinal Evaluation:")
    summary = agent.evaluate(maneuvers)
    print(f"  Max collision probability: {summary['max_collision_probability']:.2e}")
    print(f"  Fuel consumed: {summary['fuel_consumed']:.2f} m/s")
    print(f"  Maneuvers: {summary['maneuvers_applied']}")
    print(f"  Success: {summary['success']}")
    
    # Visualize
    if args.visualize:
        print("\nGenerating visualization...")
        sim = Simulator(env, maneuvers)
        sim.run()
        sim.visualize_results()


if __name__ == "__main__":
    main()
