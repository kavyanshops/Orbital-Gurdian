"""
Grid Search Agent

Searches discrete grid of maneuver options.
Supports collinear (along velocity) or full 3D search.
"""

import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from tqdm import tqdm
import copy
from itertools import product

from ...agent.base_agent import BaseAgent
from ...api.environment import SpaceEnvironment, Maneuver
from ...simulator.simulator import Simulator


class GridSearchAgent(BaseAgent):
    """
    Grid search agent for maneuver optimization.
    """
    
    def __init__(
        self,
        environment: SpaceEnvironment,
        n_maneuvers: int = 1,
        n_time_points: int = 10,
        n_magnitude_points: int = 5,
        n_angle_points: int = 8,
        mode: str = 'collinear',  # 'collinear' or '3d'
        max_delta_v: float = 5.0
    ):
        """
        Initialize Grid Search agent.
        
        Args:
            environment: Space environment
            n_maneuvers: Number of maneuvers (1 for grid, >1 is expensive)
            n_time_points: Grid points for maneuver timing
            n_magnitude_points: Grid points for delta-V magnitude
            n_angle_points: Grid points for direction (3D mode)
            mode: 'collinear' (along velocity) or '3d' (full 3D)
            max_delta_v: Maximum delta-V magnitude [m/s]
        """
        super().__init__(environment, name="GridSearchAgent")
        
        self.n_maneuvers = n_maneuvers
        self.n_time_points = n_time_points
        self.n_magnitude_points = n_magnitude_points
        self.n_angle_points = n_angle_points
        self.mode = mode
        self.max_delta_v = min(max_delta_v, environment.satellite.fuel)
        
    def _generate_grid(self) -> List[Tuple]:
        """Generate grid of maneuver options."""
        # Time grid
        time_range = self.env.end_epoch - self.env.start_epoch
        times = np.linspace(
            self.env.start_epoch + time_range * 0.1,
            self.env.start_epoch + time_range * 0.9,
            self.n_time_points
        )
        
        # Magnitude grid (include 0 for no maneuver)
        magnitudes = np.linspace(0, self.max_delta_v, self.n_magnitude_points)
        
        if self.mode == 'collinear':
            # Collinear: just prograde/retrograde
            directions = [1.0, -1.0]
            grid = list(product(times, magnitudes, directions))
        else:
            # 3D: spherical angles
            thetas = np.linspace(0, np.pi, self.n_angle_points // 2 + 1)
            phis = np.linspace(0, 2 * np.pi, self.n_angle_points)
            grid = list(product(times, magnitudes, thetas, phis))
        
        return grid
    
    def _grid_point_to_maneuver(
        self, 
        point: Tuple, 
        epoch: float
    ) -> Optional[Maneuver]:
        """Convert grid point to maneuver."""
        if self.mode == 'collinear':
            time, mag, direction = point
            if mag < 0.001:
                return None
            
            # Get velocity at maneuver time
            _, vel = self.env.satellite.get_state_at_epoch(time)
            vel_norm = vel / np.linalg.norm(vel)
            delta_v = direction * mag * vel_norm
            
        else:
            time, mag, theta, phi = point
            if mag < 0.001:
                return None
            
            # Convert spherical to Cartesian
            delta_v = mag * np.array([
                np.sin(theta) * np.cos(phi),
                np.sin(theta) * np.sin(phi),
                np.cos(theta)
            ])
        
        return Maneuver(epoch=time, delta_v=delta_v)
    
    def _evaluate(self, maneuvers: List[Maneuver]) -> float:
        """Evaluate maneuver sequence."""
        env_copy = copy.deepcopy(self.env)
        sim = Simulator(env_copy, maneuvers)
        summary = sim.run()
        
        # Score
        score = -summary['max_collision_probability'] * 1000
        score += summary['fuel_remaining'] * 0.1
        if summary['success']:
            score += 100
            
        return score
    
    def optimize(
        self,
        verbose: bool = True,
        **kwargs
    ) -> List[Maneuver]:
        """
        Run grid search optimization.
        
        Returns:
            Best maneuver list found (multiple maneuvers based on n_maneuvers)
        """
        # Override n_maneuvers if passed in kwargs
        n_maneuvers = kwargs.get('n_maneuvers', self.n_maneuvers)
        
        grid = self._generate_grid()
        
        # Collect all valid maneuvers with scores
        scored_maneuvers = []
        
        iterator = tqdm(grid, desc="Grid Search") if verbose else grid
        
        for point in iterator:
            if self.mode == 'collinear':
                time = point[0]
            else:
                time = point[0]
            
            maneuver = self._grid_point_to_maneuver(point, time)
            if maneuver is not None:
                score = self._evaluate([maneuver])
                scored_maneuvers.append((score, maneuver))
        
        # Sort by score (descending) and take top N
        scored_maneuvers.sort(key=lambda x: x[0], reverse=True)
        
        if scored_maneuvers:
            # Take top N maneuvers with different times
            selected = []
            selected_times = set()
            for score, m in scored_maneuvers:
                # Avoid selecting maneuvers at same time
                time_key = round(m.epoch, 3)
                if time_key not in selected_times:
                    selected.append(m)
                    selected_times.add(time_key)
                if len(selected) >= n_maneuvers:
                    break
            
            self.maneuvers = selected
            best_score = scored_maneuvers[0][0] if scored_maneuvers else 0
        else:
            # No valid maneuvers found - create placeholders
            time_range = self.env.end_epoch - self.env.start_epoch
            self.maneuvers = []
            for i in range(n_maneuvers):
                epoch = self.env.start_epoch + (i + 1) * time_range / (n_maneuvers + 1)
                self.maneuvers.append(Maneuver(epoch=epoch, delta_v=np.array([0.0, 0.0, 0.0])))
            best_score = 0
        
        if verbose:
            print(f"Grid Search: returning {len(self.maneuvers)} maneuvers")
        
        self.training_history.append({
            'grid_size': len(grid),
            'best_score': best_score
        })
        
        return self.maneuvers
    
    def get_action(self, state: Dict[str, Any]) -> Optional[Maneuver]:
        """Get next scheduled maneuver."""
        current_epoch = state['epoch']
        
        for m in self.maneuvers:
            if abs(m.epoch - current_epoch) < self.env.time_step_days:
                return m
        
        return None
