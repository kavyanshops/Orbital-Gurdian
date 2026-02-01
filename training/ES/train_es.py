#!/usr/bin/env python3
"""
Evolution Strategies Training Script
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from space_navigator.api.environment import SpaceEnvironment
from space_navigator.models.evolution_strategies import EvolutionStrategiesAgent
from space_navigator.simulator.simulator import Simulator


def main():
    parser = argparse.ArgumentParser(description="Train ES agent")
    parser.add_argument("--env", "-e", type=str, required=True)
    parser.add_argument("--save_path", "-o", type=str, default="results/maneuvers_es.csv")
    parser.add_argument("--n_iterations", "-i", type=int, default=100)
    parser.add_argument("--population_size", "-p", type=int, default=50)
    parser.add_argument("--learning_rate", type=float, default=0.1)
    parser.add_argument("--sigma", type=float, default=0.5)
    parser.add_argument("--n_maneuvers", "-m", type=int, default=3)
    parser.add_argument("--seed", "-s", type=int, default=None)
    parser.add_argument("--visualize", "-v", action="store_true")
    
    args = parser.parse_args()
    
    print(f"Loading environment: {args.env}")
    env = SpaceEnvironment.from_json(args.env)
    
    agent = EvolutionStrategiesAgent(
        environment=env,
        n_maneuvers=args.n_maneuvers,
        population_size=args.population_size,
        learning_rate=args.learning_rate,
        sigma=args.sigma,
        n_iterations=args.n_iterations,
        seed=args.seed
    )
    
    print(f"Training ES agent...")
    maneuvers = agent.optimize(verbose=True)
    
    Path(args.save_path).parent.mkdir(parents=True, exist_ok=True)
    agent.save_maneuvers(args.save_path)
    print(f"\nManeuvers saved to: {args.save_path}")
    
    summary = agent.evaluate(maneuvers)
    print(f"\nFinal: collision_prob={summary['max_collision_probability']:.2e}, "
          f"fuel={summary['fuel_consumed']:.2f} m/s, success={summary['success']}")
    
    if args.visualize:
        sim = Simulator(env, maneuvers)
        sim.run()
        sim.visualize_results()


if __name__ == "__main__":
    main()
