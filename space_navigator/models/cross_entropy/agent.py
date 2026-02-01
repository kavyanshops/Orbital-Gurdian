"""
Cross-Entropy Method Agent

Implements the Cross-Entropy Method for maneuver optimization.
The CE method iteratively samples and refines a distribution
over maneuver parameters.

Algorithm:
1. Initialize distribution over maneuver parameters
2. Sample N maneuver tables from distribution
3. Evaluate each via simulation
4. Select top K% (elite)
5. Update distribution toward elite mean
6. Iterate until convergence
"""

import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from tqdm import tqdm
import copy

from ...agent.base_agent import BaseAgent
from ...api.environment import SpaceEnvironment, Maneuver
from ...simulator.simulator import Simulator


def evaluate_worker(args):
    """
    Worker function for evaluation (can be used for parallel or sequential).
    Args:
        args: Tuple of (env, params, n_maneuvers)
    """
    env, params, n_maneuvers = args
    
    # Reconstruct maneuvers from params
    maneuvers = []
    for i in range(n_maneuvers):
        idx = i * 4
        epoch = params[idx]
        epoch = np.clip(epoch, env.start_epoch, env.end_epoch)
        
        delta_v = np.array([params[idx + 1], params[idx + 2], params[idx + 3]])
        
        dv_mag = np.linalg.norm(delta_v)
        max_dv = env.satellite.fuel / n_maneuvers
        if dv_mag > max_dv and dv_mag > 0:
            delta_v = delta_v * (max_dv / dv_mag)
        
        if np.linalg.norm(delta_v) > 0.001:
            maneuvers.append(Maneuver(epoch=epoch, delta_v=delta_v))
    
    maneuvers.sort(key=lambda m: m.epoch)
    
    # Run simulation
    env_copy = copy.deepcopy(env)
    sim = Simulator(env_copy, maneuvers)
    summary = sim.run()
    
    # Calculate score
    score = -summary['max_collision_probability'] * 1000
    score += summary['fuel_remaining'] * 0.1
    if summary['success']:
        score += 100
        
    return score, summary


class CrossEntropyAgent(BaseAgent):
    """
    Cross-Entropy Method agent for maneuver optimization.
    """
    
    def __init__(
        self,
        environment: SpaceEnvironment,
        n_maneuvers: int = 3,
        population_size: int = 50,
        elite_fraction: float = 0.2,
        n_iterations: int = 100,
        initial_std: float = 1.0,
        min_std: float = 0.01,
        seed: Optional[int] = None
    ):
        """
        Initialize CE agent.
        
        Args:
            environment: Space environment
            n_maneuvers: Number of maneuvers to optimize
            population_size: Number of samples per iteration
            elite_fraction: Fraction of elite samples to use
            n_iterations: Maximum optimization iterations
            initial_std: Initial standard deviation
            min_std: Minimum standard deviation
            seed: Random seed
        """
        super().__init__(environment, name="CrossEntropyAgent")
        
        self.n_maneuvers = n_maneuvers
        self.population_size = population_size
        self.elite_fraction = elite_fraction
        self.n_elite = max(1, int(population_size * elite_fraction))
        self.n_iterations = n_iterations
        self.initial_std = initial_std
        self.min_std = min_std
        
        if seed is not None:
            np.random.seed(seed)
        
        # Distribution parameters
        # Each maneuver: epoch, delta_vx, delta_vy, delta_vz
        self.param_dim = n_maneuvers * 4
        self.mean = None
        self.std = None
        
        self._initialize_distribution()
        
    def _initialize_distribution(self):
        """Initialize distribution over maneuver parameters."""
        # Initialize means
        self.mean = np.zeros(self.param_dim)
        
        # Spread maneuver epochs evenly
        time_range = self.env.end_epoch - self.env.start_epoch
        for i in range(self.n_maneuvers):
            epoch_idx = i * 4
            self.mean[epoch_idx] = self.env.start_epoch + time_range * (i + 1) / (self.n_maneuvers + 1)
        
        # Initial delta-V means are zero (no maneuver)
        
        # Standard deviations
        self.std = np.ones(self.param_dim) * self.initial_std
        # Larger std for epoch (scaled to time range)
        for i in range(self.n_maneuvers):
            self.std[i * 4] = time_range * 0.2
        
    def _sample_population(self) -> np.ndarray:
        """Sample population of maneuver parameters."""
        samples = np.random.normal(
            loc=self.mean,
            scale=self.std,
            size=(self.population_size, self.param_dim)
        )
        return samples
    
    def _params_to_maneuvers(self, params: np.ndarray) -> List[Maneuver]:
        """Convert parameter vector to maneuver list."""
        maneuvers = []
        
        for i in range(self.n_maneuvers):
            idx = i * 4
            epoch = params[idx]
            epoch = np.clip(epoch, self.env.start_epoch, self.env.end_epoch)
            
            delta_v = np.array([
                params[idx + 1],
                params[idx + 2],
                params[idx + 3]
            ])
            
            dv_mag = np.linalg.norm(delta_v)
            max_dv = self.env.satellite.fuel / self.n_maneuvers
            if dv_mag > max_dv and dv_mag > 0:
                delta_v = delta_v * (max_dv / dv_mag)
            
            if np.linalg.norm(delta_v) > 0.001:
                maneuvers.append(Maneuver(epoch=epoch, delta_v=delta_v))
        
        maneuvers.sort(key=lambda m: m.epoch)
        return maneuvers
    
    def optimize(
        self,
        verbose: bool = True,
        early_stop_threshold: float = 1e-5,
        **kwargs
    ) -> List[Maneuver]:
        """
        Run Cross-Entropy optimization.
        
        Args:
            verbose: Print progress
            early_stop_threshold: Stop if collision prob below this
            
        Returns:
            Optimized maneuver list
        """
        best_score = float('-inf')
        best_params = self.mean.copy()
        best_summary = None
        
        iterator = tqdm(range(self.n_iterations), desc="CE Optimization") if verbose else range(self.n_iterations)
        
        for iteration in iterator:
            # Sample population
            population = self._sample_population()
            
            # Evaluate all samples (sequential for stability)
            scores = []
            summaries = []
            
            for params in population:
                score, summary = evaluate_worker((self.env, params, self.n_maneuvers))
                scores.append(score)
                summaries.append(summary)
            
            scores = np.array(scores)
            
            # Select elite
            elite_indices = np.argsort(scores)[-self.n_elite:]
            elite_samples = population[elite_indices]
            elite_scores = scores[elite_indices]
            
            # Update distribution
            self.mean = np.mean(elite_samples, axis=0)
            self.std = np.std(elite_samples, axis=0) + self.min_std
            
            # Track best
            if elite_scores[-1] > best_score:
                best_score = elite_scores[-1]
                best_params = elite_samples[-1].copy()
                best_summary = summaries[elite_indices[-1]]
            
            # Record history
            self.training_history.append({
                'iteration': iteration,
                'best_score': best_score,
                'mean_score': np.mean(scores),
                'max_collision_prob': best_summary['max_collision_probability'] if best_summary else 1.0
            })
            
            if verbose:
                tqdm.write(f"Iter {iteration}: best_score={best_score:.2f}, "
                          f"collision_prob={best_summary['max_collision_probability']:.2e}")
            
            # Early stopping
            if best_summary and best_summary['max_collision_probability'] < early_stop_threshold:
                if verbose:
                    tqdm.write(f"Early stopping - threshold reached!")
                break
        
        # Convert best params to maneuvers
        self.maneuvers = self._params_to_maneuvers(best_params)
        
        return self.maneuvers
    
    def get_action(self, state: Dict[str, Any]) -> Optional[Maneuver]:
        """Get next scheduled maneuver if epoch matches."""
        current_epoch = state['epoch']
        
        for m in self.maneuvers:
            if abs(m.epoch - current_epoch) < self.env.time_step_days:
                return m
        
        return None
    
    def get_training_curve(self) -> Dict[str, List]:
        """Get training curves for plotting."""
        return {
            'iterations': [h['iteration'] for h in self.training_history],
            'best_scores': [h['best_score'] for h in self.training_history],
            'mean_scores': [h['mean_score'] for h in self.training_history],
            'collision_probs': [h['max_collision_prob'] for h in self.training_history]
        }
