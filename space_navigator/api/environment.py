"""
Space Environment Module

Defines the space environment with protected satellite, debris objects,
and RL-compatible interfaces for state/action/reward.
"""

import json
import math
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .orbital_mechanics import OrbitalElements, OrbitalMechanics, MU_EARTH, SECONDS_PER_DAY


@dataclass
class SpaceObject:
    """
    Base class for space objects (satellites and debris).
    """
    name: str
    orbital_elements: OrbitalElements
    radius: float = 1.0  # Cross-section radius [m]
    
    def get_state_at_epoch(self, epoch: float) -> Tuple[np.ndarray, np.ndarray]:
        """Get position and velocity at epoch."""
        return OrbitalMechanics.get_position_at_epoch(self.orbital_elements, epoch)


@dataclass
class Satellite(SpaceObject):
    """
    Protected satellite with propulsion capabilities.
    """
    mass: float = 500.0           # Mass [kg]
    fuel: float = 50.0            # Fuel capacity [m/s delta-V equivalent]
    max_thrust: float = 1.0       # Maximum thrust acceleration [m/s²]
    current_fuel: float = field(default=None)  # type: ignore
    
    def __post_init__(self):
        if self.current_fuel is None:
            self.current_fuel = self.fuel
    
    def apply_maneuver(self, delta_v: np.ndarray) -> bool:
        """
        Apply delta-V maneuver if fuel available.
        
        Args:
            delta_v: Delta-V vector [m/s]
            
        Returns:
            True if maneuver applied, False if insufficient fuel
        """
        dv_magnitude = float(np.linalg.norm(delta_v))
        
        if dv_magnitude > self.current_fuel:
            return False
        
        # Apply maneuver to orbital elements
        self.orbital_elements = OrbitalMechanics.apply_delta_v(
            self.orbital_elements, delta_v
        )
        self.current_fuel -= dv_magnitude
        return True


@dataclass
class Debris(SpaceObject):
    """Space debris object (passive, no propulsion)."""
    pass


@dataclass
class Thresholds:
    """Configuration thresholds for the environment."""
    collision_prob: float = 1e-4
    fuel_consumption: float = 10.0  # Max delta-V [m/s]
    trajectory_deviation: List[Optional[float]] = field(
        default_factory=lambda: [100.0, 0.01, 0.01, 0.01, 0.01, None]
    )


@dataclass
class Maneuver:
    """Represents a single impulsive maneuver."""
    epoch: float  # MJD2000
    delta_v: np.ndarray  # [vx, vy, vz] in m/s
    
    def to_dict(self) -> Dict:
        return {
            'epoch_mjd2000': self.epoch,
            'delta_vx': self.delta_v[0],
            'delta_vy': self.delta_v[1],
            'delta_vz': self.delta_v[2]
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Maneuver':
        return cls(
            epoch=d['epoch_mjd2000'],
            delta_v=np.array([d['delta_vx'], d['delta_vy'], d['delta_vz']])
        )


class SpaceEnvironment:
    """
    RL-compatible space environment for maneuver optimization.
    
    State Space:
        - Current epoch
        - Satellite: position (x,y,z), velocity (vx,vy,vz)
        - Each debris: position, velocity
        - Remaining fuel
        - Time to next conjunction
        - Current collision probabilities per debris
        
    Action Space:
        - Maneuver timing (when to apply thrust)
        - Delta-V vector (direction and magnitude)
    """
    
    def __init__(
        self,
        satellite: Satellite,
        debris: List[Debris],
        start_epoch: float,
        end_epoch: float,
        thresholds: Optional[Thresholds] = None,
        time_step: float = 60.0,  # seconds
        reward_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize space environment.
        
        Args:
            satellite: Protected satellite object
            debris: List of debris objects
            start_epoch: Start time [MJD2000]
            end_epoch: End time [MJD2000]
            thresholds: Configuration thresholds
            time_step: Simulation time step [s]
            reward_weights: Weights for reward function (w1, w2, w3)
        """
        self.satellite = satellite
        self.debris = debris
        self.start_epoch = start_epoch
        self.end_epoch = end_epoch
        self.thresholds = thresholds or Thresholds()
        self.time_step = time_step
        self.time_step_days = time_step / SECONDS_PER_DAY
        
        # Reward weights
        self.reward_weights = reward_weights or {
            'collision': 1000.0,  # w1
            'fuel': 10.0,         # w2
            'deviation': 1.0      # w3
        }
        
        # Initial state tracking
        self.initial_elements = OrbitalElements(
            a=satellite.orbital_elements.a,
            e=satellite.orbital_elements.e,
            i=satellite.orbital_elements.i,
            raan=satellite.orbital_elements.raan,
            omega=satellite.orbital_elements.omega,
            M=satellite.orbital_elements.M,
            epoch=satellite.orbital_elements.epoch
        )
        
        # Current state
        self.current_epoch = start_epoch
        self.maneuvers_applied: List[Maneuver] = []
        self.collision_history: List[Dict] = []
        
    def reset(self) -> Dict[str, Any]:
        """Reset environment to initial state."""
        self.satellite.orbital_elements = OrbitalElements(
            a=self.initial_elements.a,
            e=self.initial_elements.e,
            i=self.initial_elements.i,
            raan=self.initial_elements.raan,
            omega=self.initial_elements.omega,
            M=self.initial_elements.M,
            epoch=self.initial_elements.epoch
        )
        self.satellite.current_fuel = self.satellite.fuel
        self.current_epoch = self.start_epoch
        self.maneuvers_applied = []
        self.collision_history = []
        
        return self.get_state()
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current state as dictionary.
        
        Returns:
            State dictionary with satellite/debris positions and metadata
        """
        # Satellite state
        sat_pos, sat_vel = self.satellite.get_state_at_epoch(self.current_epoch)
        
        # Debris states
        debris_states = []
        collision_probs = []
        
        for deb in self.debris:
            deb_pos, deb_vel = deb.get_state_at_epoch(self.current_epoch)
            distance = OrbitalMechanics.calculate_distance(sat_pos, deb_pos)
            
            debris_states.append({
                'name': deb.name,
                'position': deb_pos.tolist(),
                'velocity': deb_vel.tolist(),
                'distance': distance
            })
            
            # Simple collision probability (simplified)
            collision_probs.append(self._estimate_collision_prob(distance, deb.radius))
        
        return {
            'epoch': self.current_epoch,
            'satellite': {
                'position': sat_pos.tolist(),
                'velocity': sat_vel.tolist(),
                'fuel_remaining': self.satellite.current_fuel
            },
            'debris': debris_states,
            'collision_probabilities': collision_probs,
            'total_collision_prob': sum(collision_probs),
            'time_remaining': self.end_epoch - self.current_epoch
        }
    
    def step(self, action: Optional[Maneuver] = None) -> Tuple[Dict, float, bool, Dict]:
        """
        Execute one time step with optional maneuver.
        
        Args:
            action: Optional maneuver to apply
            
        Returns:
            Tuple of (next_state, reward, done, info)
        """
        info = {'maneuver_applied': False, 'fuel_used': 0.0}
        
        # Apply maneuver if provided
        if action is not None:
            dv_magnitude = float(np.linalg.norm(action.delta_v))
            if self.satellite.apply_maneuver(action.delta_v):
                self.maneuvers_applied.append(action)
                info['maneuver_applied'] = True
                info['fuel_used'] = dv_magnitude
        
        # Advance time
        self.current_epoch += self.time_step_days
        
        # Propagate satellite
        dt = self.time_step
        self.satellite.orbital_elements = OrbitalMechanics.propagate(
            self.satellite.orbital_elements, dt
        )
        
        # Get new state
        state = self.get_state()
        
        # Calculate reward
        reward = self._calculate_reward(state, info)
        
        # Check if done
        done = self.current_epoch >= self.end_epoch
        
        # Store collision info
        self.collision_history.append({
            'epoch': self.current_epoch,
            'collision_prob': state['total_collision_prob']
        })
        
        return state, reward, done, info
    
    def _estimate_collision_prob(self, distance: float, debris_radius: float) -> float:
        """
        Simplified collision probability estimate.
        
        For full Chen-Bai implementation, see collision_probability.py
        """
        combined_radius = self.satellite.radius + debris_radius
        
        # Very simplified - exponential decay with distance
        if distance < combined_radius:
            return 1.0
        elif distance < 1000:  # Within 1 km
            return math.exp(-(distance - combined_radius) / 100)
        elif distance < 10000:  # Within 10 km
            return math.exp(-(distance - combined_radius) / 1000) * 0.1
        else:
            return 1e-8
    
    def _calculate_reward(self, state: Dict, info: Dict) -> float:
        """
        Calculate reward: 
        reward = -w1*collision_prob - w2*fuel_consumed - w3*trajectory_deviation
        """
        w = self.reward_weights
        
        # Collision probability penalty
        collision_penalty = w['collision'] * state['total_collision_prob']
        
        # Fuel consumption penalty
        fuel_penalty = w['fuel'] * info['fuel_used']
        
        # Trajectory deviation penalty
        deviation = self._calculate_deviation()
        deviation_penalty = w['deviation'] * deviation
        
        reward = -(collision_penalty + fuel_penalty + deviation_penalty)
        
        return reward
    
    def _calculate_deviation(self) -> float:
        """Calculate trajectory deviation from target orbit."""
        current = self.satellite.orbital_elements
        target = self.initial_elements
        thresholds = self.thresholds.trajectory_deviation
        
        deviations = [
            abs(current.a - target.a) / (thresholds[0] or 1e10),
            abs(current.e - target.e) / (thresholds[1] or 1e10),
            abs(current.i - target.i) / (thresholds[2] or 1e10),
            abs(current.raan - target.raan) / (thresholds[3] or 1e10),
            abs(current.omega - target.omega) / (thresholds[4] or 1e10),
        ]
        
        return sum(d for d in deviations if d is not None)
    
    def get_observation_space_size(self) -> int:
        """Get size of flattened observation vector."""
        # satellite: pos(3) + vel(3) + fuel(1) = 7
        # per debris: pos(3) + vel(3) + distance(1) = 7
        # metadata: epoch(1) + time_remaining(1) = 2
        return 7 + len(self.debris) * 7 + 2
    
    def get_action_space_size(self) -> int:
        """Get size of action vector (delta-V x,y,z)."""
        return 3
    
    def state_to_vector(self, state: Dict) -> np.ndarray:
        """Convert state dict to flat vector for RL."""
        vec = []
        
        # Satellite
        vec.extend(state['satellite']['position'])
        vec.extend(state['satellite']['velocity'])
        vec.append(state['satellite']['fuel_remaining'])
        
        # Debris
        for deb in state['debris']:
            vec.extend(deb['position'])
            vec.extend(deb['velocity'])
            vec.append(deb['distance'])
        
        # Metadata
        vec.append(state['epoch'])
        vec.append(state['time_remaining'])
        
        return np.array(vec)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'SpaceEnvironment':
        """Load environment from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Parse satellite
        sat_data = data['protected']
        satellite = Satellite(
            name=sat_data['name'],
            orbital_elements=OrbitalElements.from_list(
                sat_data['orbital_elements'],
                data.get('start_epoch', 0)
            ),
            radius=sat_data.get('radius', 5),
            mass=sat_data.get('mass', 500),
            fuel=sat_data.get('fuel', 50)
        )
        
        # Parse debris
        debris_list = []
        for deb_data in data.get('debris', []):
            debris_list.append(Debris(
                name=deb_data['name'],
                orbital_elements=OrbitalElements.from_list(
                    deb_data['orbital_elements'],
                    data.get('start_epoch', 0)
                ),
                radius=deb_data.get('radius', 0.1)
            ))
        
        # Parse thresholds
        thresh_data = data.get('thresholds', {})
        thresholds = Thresholds(
            collision_prob=thresh_data.get('collision_prob', 1e-4),
            fuel_consumption=thresh_data.get('fuel_consumption', 10),
            trajectory_deviation=thresh_data.get('trajectory_deviation', 
                                                  [100, 0.01, 0.01, 0.01, 0.01, None])
        )
        
        return cls(
            satellite=satellite,
            debris=debris_list,
            start_epoch=data.get('start_epoch', 0),
            end_epoch=data.get('end_epoch', 0.1),
            thresholds=thresholds
        )
    
    def to_json(self, filepath: str):
        """Save environment to JSON file."""
        data = {
            'protected': {
                'name': self.satellite.name,
                'orbital_elements': self.satellite.orbital_elements.to_list(),
                'mass': self.satellite.mass,
                'fuel': self.satellite.fuel,
                'radius': self.satellite.radius
            },
            'debris': [
                {
                    'name': deb.name,
                    'orbital_elements': deb.orbital_elements.to_list(),
                    'radius': deb.radius
                }
                for deb in self.debris
            ],
            'start_epoch': self.start_epoch,
            'end_epoch': self.end_epoch,
            'thresholds': {
                'collision_prob': self.thresholds.collision_prob,
                'fuel_consumption': self.thresholds.fuel_consumption,
                'trajectory_deviation': self.thresholds.trajectory_deviation
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
