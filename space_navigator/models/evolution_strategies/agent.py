"""
Evolution Strategies Agent

Population-based optimization using Evolution Strategies.
Supports optional PyTorch neural network policy.
"""

import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from tqdm import tqdm
import copy

from ...agent.base_agent import BaseAgent
from ...api.environment import SpaceEnvironment, Maneuver
from ...simulator.simulator import Simulator

# Optional PyTorch support
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class EvolutionStrategiesAgent(BaseAgent):
    """
    Evolution Strategies agent for maneuver optimization.
    """
    
    def __init__(
        self,
        environment: SpaceEnvironment,
        n_maneuvers: int = 3,
        population_size: int = 50,
        learning_rate: float = 0.1,
        sigma: float = 0.5,
        n_iterations: int = 100,
        use_neural_network: bool = False,
        seed: Optional[int] = None
    ):
        """
        Initialize ES agent.
        
        Args:
            environment: Space environment
            n_maneuvers: Number of maneuvers to optimize
            population_size: Population size (should be even)
            learning_rate: Learning rate for gradient update
            sigma: Noise standard deviation
            n_iterations: Maximum iterations
            use_neural_network: Use neural network policy
            seed: Random seed
        """
        super().__init__(environment, name="EvolutionStrategiesAgent")
        
        self.n_maneuvers = n_maneuvers
        self.population_size = population_size - (population_size % 2)  # Make even
        self.learning_rate = learning_rate
        self.sigma = sigma
        self.n_iterations = n_iterations
        self.use_nn = use_neural_network and TORCH_AVAILABLE
        
        if seed is not None:
            np.random.seed(seed)
            if TORCH_AVAILABLE:
                torch.manual_seed(seed)
        
        # Parameter dimension
        self.param_dim = n_maneuvers * 4  # epoch, dv_x, dv_y, dv_z
        
        # Initialize parameters
        self.params = self._initialize_params()
        
        # Neural network (if enabled)
        self.policy_net = None
        if self.use_nn:
            self._build_network()
    
    def _initialize_params(self) -> np.ndarray:
        """Initialize maneuver parameters."""
        params = np.zeros(self.param_dim)
        
        # Initialize epochs evenly distributed
        time_range = self.env.end_epoch - self.env.start_epoch
        for i in range(self.n_maneuvers):
            params[i * 4] = self.env.start_epoch + time_range * (i + 1) / (self.n_maneuvers + 1)
        
        return params
    
    def _build_network(self):
        """Build neural network policy."""
        if not TORCH_AVAILABLE:
            return
        
        state_dim = self.env.get_observation_space_size()
        action_dim = 3  # delta-V vector
        
        self.policy_net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_dim),
            nn.Tanh()  # Bound outputs to [-1, 1]
        )
    
    def _params_to_maneuvers(self, params: np.ndarray) -> List[Maneuver]:
        """Convert parameter vector to maneuver list."""
        maneuvers = []
        
        for i in range(self.n_maneuvers):
            idx = i * 4
            epoch = np.clip(params[idx], self.env.start_epoch, self.env.end_epoch)
            
            delta_v = np.array([
                params[idx + 1],
                params[idx + 2],
                params[idx + 3]
            ])
            
            # Clamp magnitude
            dv_mag = np.linalg.norm(delta_v)
            max_dv = self.env.satellite.fuel / self.n_maneuvers
            if dv_mag > max_dv and dv_mag > 0:
                delta_v = delta_v * (max_dv / dv_mag)
            
            if np.linalg.norm(delta_v) > 0.001:
                maneuvers.append(Maneuver(epoch=epoch, delta_v=delta_v))
        
        maneuvers.sort(key=lambda m: m.epoch)
        return maneuvers
    
    def _evaluate(self, params: np.ndarray) -> float:
        """Evaluate fitness of parameters."""
        maneuvers = self._params_to_maneuvers(params)
        
        env_copy = copy.deepcopy(self.env)
        sim = Simulator(env_copy, maneuvers)
        summary = sim.run()
        
        # Fitness (negative cost)
        fitness = -summary['max_collision_probability'] * 1000
        fitness += summary['fuel_remaining'] * 0.1
        
        if summary['success']:
            fitness += 100
            
        return fitness
    
    def optimize(
        self,
        verbose: bool = True,
        **kwargs
    ) -> List[Maneuver]:
        """
        Run Evolution Strategies optimization.
        
        Returns:
            Optimized maneuver list
        """
        best_fitness = float('-inf')
        best_params = self.params.copy()
        
        iterator = tqdm(range(self.n_iterations), desc="ES Optimization") if verbose else range(self.n_iterations)
        
        for iteration in iterator:
            # Generate perturbations (antithetic sampling)
            noise = np.random.randn(self.population_size // 2, self.param_dim)
            noise = np.vstack([noise, -noise])  # Antithetic pairs
            
            # Evaluate population
            fitness_values = []
            for eps in noise:
                perturbed_params = self.params + self.sigma * eps
                fitness = self._evaluate(perturbed_params)
                fitness_values.append(fitness)
            
            fitness_values = np.array(fitness_values)
            
            # Normalize fitness for gradient estimation
            fitness_normalized = (fitness_values - np.mean(fitness_values))
            std = np.std(fitness_values)
            if std > 0:
                fitness_normalized /= std
            
            # Estimate gradient
            gradient = np.mean(
                fitness_normalized[:, np.newaxis] * noise,
                axis=0
            )
            
            # Update parameters
            self.params += self.learning_rate * gradient
            
            # Track best
            current_fitness = self._evaluate(self.params)
            if current_fitness > best_fitness:
                best_fitness = current_fitness
                best_params = self.params.copy()
            
            # Record history
            self.training_history.append({
                'iteration': iteration,
                'best_fitness': best_fitness,
                'mean_fitness': np.mean(fitness_values)
            })
            
            if verbose and iteration % 10 == 0:
                tqdm.write(f"Iter {iteration}: best_fitness={best_fitness:.2f}, mean={np.mean(fitness_values):.2f}")
        
        self.params = best_params
        self.maneuvers = self._params_to_maneuvers(self.params)
        
        return self.maneuvers
    
    def get_action(self, state: Dict[str, Any]) -> Optional[Maneuver]:
        """Get next scheduled maneuver."""
        current_epoch = state['epoch']
        
        for m in self.maneuvers:
            if abs(m.epoch - current_epoch) < self.env.time_step_days:
                return m
        
        return None
