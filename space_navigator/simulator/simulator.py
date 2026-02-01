"""
Simulator Module

Main simulation loop with 3D visualization using matplotlib.
Runs the space environment forward in time, tracks conjunctions,
applies maneuvers, and visualizes results.
"""

import math
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.animation import FuncAnimation
from typing import List, Dict, Optional, Callable
import csv
from pathlib import Path

from ..api.environment import SpaceEnvironment, Maneuver
from ..api.orbital_mechanics import OrbitalMechanics, EARTH_RADIUS, SECONDS_PER_DAY
from ..collision.collision_probability import CollisionProbability, compute_cumulative_probability


class Simulator:
    """
    Main simulation engine with visualization capabilities.
    """
    
    def __init__(
        self,
        environment: SpaceEnvironment,
        maneuvers: Optional[List[Maneuver]] = None,
        visualize: bool = False,
        real_time_plot: bool = False
    ):
        """
        Initialize simulator.
        
        Args:
            environment: Space environment to simulate
            maneuvers: Pre-planned maneuver schedule (optional)
            visualize: Enable 3D visualization
            real_time_plot: Update plots in real-time
        """
        self.env = environment
        self.maneuvers = maneuvers or []
        self.visualize = visualize
        self.real_time_plot = real_time_plot
        
        # Results storage
        self.history: List[Dict] = []
        self.trajectory_data = {
            'satellite': [],
            'debris': {deb.name: [] for deb in environment.debris}
        }
        self.collision_probs: List[float] = []
        self.rewards: List[float] = []
        self.fuel_history: List[float] = []
        
        # Visualization
        self.fig = None
        self.ax = None
        
    def reset(self):
        """Reset simulation state."""
        self.env.reset()
        self.history = []
        self.trajectory_data = {
            'satellite': [],
            'debris': {deb.name: [] for deb in self.env.debris}
        }
        self.collision_probs = []
        self.rewards = []
        self.fuel_history = []
        
    def run(self, callback: Optional[Callable] = None) -> Dict:
        """
        Run full simulation from start to end epoch.
        
        Args:
            callback: Optional function called each step with (state, info)
            
        Returns:
            Summary dictionary with results
        """
        self.reset()
        state = self.env.get_state()
        
        total_reward = 0.0
        step = 0
        maneuver_idx = 0
        
        while self.env.current_epoch < self.env.end_epoch:
            # Check for scheduled maneuver
            action = None
            if maneuver_idx < len(self.maneuvers):
                next_maneuver = self.maneuvers[maneuver_idx]
                if self.env.current_epoch >= next_maneuver.epoch:
                    action = next_maneuver
                    maneuver_idx += 1
            
            # Execute step
            state, reward, done, info = self.env.step(action)
            total_reward += reward
            
            # Store history
            self._record_step(state, reward, info)
            
            # Callback
            if callback:
                callback(state, info)
            
            step += 1
            
            if done:
                break
        
        # Compute summary
        summary = self._compute_summary(total_reward, step)
        
        return summary
    
    def _record_step(self, state: Dict, reward: float, info: Dict):
        """Record step data for analysis and visualization."""
        # State history
        self.history.append({
            'epoch': state['epoch'],
            'state': state,
            'reward': reward,
            'info': info
        })
        
        # Trajectory data
        self.trajectory_data['satellite'].append(
            state['satellite']['position']
        )
        
        for deb in state['debris']:
            self.trajectory_data['debris'][deb['name']].append(deb['position'])
        
        # Metrics
        self.collision_probs.append(state['total_collision_prob'])
        self.rewards.append(reward)
        self.fuel_history.append(state['satellite']['fuel_remaining'])
        
    def _compute_summary(self, total_reward: float, steps: int) -> Dict:
        """Compute simulation summary statistics."""
        max_prob = max(self.collision_probs) if self.collision_probs else 0
        cumulative_prob = compute_cumulative_probability(self.collision_probs)
        fuel_consumed = self.env.satellite.fuel - self.env.satellite.current_fuel
        
        return {
            'total_steps': steps,
            'total_reward': total_reward,
            'max_collision_probability': max_prob,
            'cumulative_collision_probability': cumulative_prob,
            'fuel_consumed': fuel_consumed,
            'fuel_remaining': self.env.satellite.current_fuel,
            'maneuvers_applied': len(self.env.maneuvers_applied),
            'threshold_exceeded': max_prob > self.env.thresholds.collision_prob,
            'success': (
                cumulative_prob < self.env.thresholds.collision_prob and
                fuel_consumed < self.env.thresholds.fuel_consumption
            )
        }
    
    def visualize_results(self, save_path: Optional[str] = None):
        """
        Create 3D visualization of simulation results.
        
        Args:
            save_path: Optional path to save figure
        """
        fig = plt.figure(figsize=(16, 10))
        
        # 3D orbit plot
        ax1 = fig.add_subplot(2, 2, 1, projection='3d')
        self._plot_3d_orbits(ax1)
        
        # Collision probability over time
        ax2 = fig.add_subplot(2, 2, 2)
        self._plot_collision_prob(ax2)
        
        # Fuel consumption
        ax3 = fig.add_subplot(2, 2, 3)
        self._plot_fuel(ax3)
        
        # Cumulative reward
        ax4 = fig.add_subplot(2, 2, 4)
        self._plot_rewards(ax4)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            
        plt.show()
        
        return fig
    
    def _plot_3d_orbits(self, ax: Axes3D):
        """Plot 3D orbital trajectories."""
        # Plot Earth
        u, v = np.mgrid[0:2*np.pi:30j, 0:np.pi:20j]
        x = EARTH_RADIUS * np.cos(u) * np.sin(v)
        y = EARTH_RADIUS * np.sin(u) * np.sin(v)
        z = EARTH_RADIUS * np.cos(v)
        ax.plot_wireframe(x, y, z, color='blue', alpha=0.3, linewidth=0.5)
        
        # Plot satellite trajectory
        if self.trajectory_data['satellite']:
            sat_traj = np.array(self.trajectory_data['satellite'])
            ax.plot(sat_traj[:, 0], sat_traj[:, 1], sat_traj[:, 2],
                   'c-', linewidth=2, label='Satellite')
            # Mark start and end
            ax.scatter(*sat_traj[0], c='green', s=100, marker='o', label='Start')
            ax.scatter(*sat_traj[-1], c='red', s=100, marker='x', label='End')
        
        # Plot debris trajectories
        colors = plt.cm.Oranges(np.linspace(0.3, 0.9, len(self.trajectory_data['debris'])))
        for (name, traj), color in zip(self.trajectory_data['debris'].items(), colors):
            if traj:
                deb_traj = np.array(traj)
                ax.plot(deb_traj[:, 0], deb_traj[:, 1], deb_traj[:, 2],
                       '-', color=color, linewidth=1, alpha=0.7, label=name)
        
        # Plot maneuvers
        for maneuver in self.env.maneuvers_applied:
            pos, _ = self.env.satellite.get_state_at_epoch(maneuver.epoch)
            ax.quiver(*pos, *maneuver.delta_v * 1e5,  # Scale for visibility
                     color='yellow', arrow_length_ratio=0.3, linewidth=2)
        
        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        ax.set_zlabel('Z [m]')
        ax.set_title('3D Orbital Trajectories')
        ax.legend(loc='upper left', fontsize=8)
        
    def _plot_collision_prob(self, ax):
        """Plot collision probability over time."""
        if not self.collision_probs:
            return
            
        epochs = [h['epoch'] for h in self.history]
        
        ax.semilogy(epochs, self.collision_probs, 'r-', linewidth=1.5)
        ax.axhline(y=self.env.thresholds.collision_prob, 
                  color='orange', linestyle='--', label='Threshold')
        
        ax.set_xlabel('Epoch [MJD2000]')
        ax.set_ylabel('Collision Probability')
        ax.set_title('Collision Probability Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
    def _plot_fuel(self, ax):
        """Plot fuel consumption over time."""
        if not self.fuel_history:
            return
            
        epochs = [h['epoch'] for h in self.history]
        
        ax.plot(epochs, self.fuel_history, 'g-', linewidth=1.5)
        ax.axhline(y=0, color='red', linestyle='--', label='Empty')
        
        ax.set_xlabel('Epoch [MJD2000]')
        ax.set_ylabel('Fuel Remaining [m/s ΔV]')
        ax.set_title('Fuel Consumption')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
    def _plot_rewards(self, ax):
        """Plot cumulative rewards over time."""
        if not self.rewards:
            return
            
        epochs = [h['epoch'] for h in self.history]
        cumulative = np.cumsum(self.rewards)
        
        ax.plot(epochs, cumulative, 'b-', linewidth=1.5)
        
        ax.set_xlabel('Epoch [MJD2000]')
        ax.set_ylabel('Cumulative Reward')
        ax.set_title('RL Reward Over Time')
        ax.grid(True, alpha=0.3)
    
    @staticmethod
    def load_maneuvers(filepath: str) -> List[Maneuver]:
        """
        Load maneuver schedule from CSV file.
        
        CSV format: epoch_mjd2000,delta_vx,delta_vy,delta_vz
        """
        maneuvers = []
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                maneuvers.append(Maneuver(
                    epoch=float(row['epoch_mjd2000']),
                    delta_v=np.array([
                        float(row['delta_vx']),
                        float(row['delta_vy']),
                        float(row['delta_vz'])
                    ])
                ))
        
        return maneuvers
    
    @staticmethod
    def save_maneuvers(maneuvers: List[Maneuver], filepath: str):
        """Save maneuver schedule to CSV file."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'epoch_mjd2000', 'delta_vx', 'delta_vy', 'delta_vz'
            ])
            writer.writeheader()
            for m in maneuvers:
                writer.writerow(m.to_dict())


def run_simulation(
    env_path: str,
    maneuvers_path: Optional[str] = None,
    visualize: bool = True,
    output_path: Optional[str] = None
) -> Dict:
    """
    Convenience function to run a full simulation.
    
    Args:
        env_path: Path to environment JSON file
        maneuvers_path: Optional path to maneuvers CSV
        visualize: Show 3D visualization
        output_path: Optional path to save results figure
        
    Returns:
        Simulation summary
    """
    # Load environment
    env = SpaceEnvironment.from_json(env_path)
    
    # Load maneuvers if provided
    maneuvers = None
    if maneuvers_path:
        maneuvers = Simulator.load_maneuvers(maneuvers_path)
    
    # Create and run simulator
    sim = Simulator(env, maneuvers, visualize=visualize)
    summary = sim.run()
    
    # Visualize if requested
    if visualize:
        sim.visualize_results(save_path=output_path)
    
    return summary
