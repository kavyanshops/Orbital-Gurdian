"""
Orbital Mechanics Engine

Pure Keplerian orbit propagation without external dependencies.
Implements Kepler's equation solver and orbital element conversions.

References:
- Vallado, "Fundamentals of Astrodynamics and Applications"
- Curtis, "Orbital Mechanics for Engineering Students"
"""

import math
import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass


# Constants
MU_EARTH = 3.986004418e14  # Earth gravitational parameter [m³/s²]
EARTH_RADIUS = 6.371e6     # Earth radius [m]
J2000_MJD = 51544.5        # J2000 epoch in MJD
MJD2000_OFFSET = 51544.0   # MJD2000 = MJD - 51544.0
SECONDS_PER_DAY = 86400.0
TWO_PI = 2.0 * math.pi


@dataclass
class OrbitalElements:
    """
    Classical Keplerian orbital elements.
    
    Attributes:
        a: Semi-major axis [m]
        e: Eccentricity [-]
        i: Inclination [rad]
        raan: Right ascension of ascending node [rad]
        omega: Argument of periapsis [rad]
        M: Mean anomaly [rad]
        epoch: Reference epoch [MJD2000]
    """
    a: float      # Semi-major axis [m]
    e: float      # Eccentricity
    i: float      # Inclination [rad]
    raan: float   # Right Ascension of Ascending Node [rad]
    omega: float  # Argument of Periapsis [rad]
    M: float      # Mean anomaly [rad]
    epoch: float  # Epoch in MJD2000
    
    @classmethod
    def from_list(cls, elements: List[float], epoch: float = 0.0) -> 'OrbitalElements':
        """Create from list [a, e, i, raan, omega, M]."""
        return cls(
            a=elements[0],
            e=elements[1],
            i=elements[2],
            raan=elements[3],
            omega=elements[4],
            M=elements[5],
            epoch=epoch
        )
    
    def to_list(self) -> List[float]:
        """Convert to list [a, e, i, raan, omega, M]."""
        return [self.a, self.e, self.i, self.raan, self.omega, self.M]


class OrbitalMechanics:
    """
    Orbital mechanics engine for Keplerian orbit propagation.
    """
    
    @staticmethod
    def solve_kepler(M: float, e: float, tol: float = 1e-10, max_iter: int = 50) -> float:
        """
        Solve Kepler's equation M = E - e*sin(E) using Newton-Raphson.
        
        Args:
            M: Mean anomaly [rad]
            e: Eccentricity
            tol: Convergence tolerance
            max_iter: Maximum iterations
            
        Returns:
            Eccentric anomaly E [rad]
        """
        # Normalize M to [0, 2π]
        M = M % TWO_PI
        
        # Initial guess (better for high eccentricity)
        if e < 0.8:
            E = M
        else:
            E = math.pi
        
        # Newton-Raphson iteration
        for _ in range(max_iter):
            f = E - e * math.sin(E) - M
            f_prime = 1.0 - e * math.cos(E)
            
            if abs(f_prime) < 1e-12:
                break
                
            E_new = E - f / f_prime
            
            if abs(E_new - E) < tol:
                return E_new
            
            E = E_new
        
        return E
    
    @staticmethod
    def eccentric_to_true_anomaly(E: float, e: float) -> float:
        """
        Convert eccentric anomaly to true anomaly.
        
        Args:
            E: Eccentric anomaly [rad]
            e: Eccentricity
            
        Returns:
            True anomaly [rad]
        """
        beta = e / (1.0 + math.sqrt(1.0 - e * e))
        nu = E + 2.0 * math.atan2(
            beta * math.sin(E),
            1.0 - beta * math.cos(E)
        )
        return nu
    
    @staticmethod
    def mean_motion(a: float, mu: float = MU_EARTH) -> float:
        """
        Calculate mean motion from semi-major axis.
        
        Args:
            a: Semi-major axis [m]
            mu: Gravitational parameter [m³/s²]
            
        Returns:
            Mean motion [rad/s]
        """
        return math.sqrt(mu / (a ** 3))
    
    @staticmethod
    def orbital_period(a: float, mu: float = MU_EARTH) -> float:
        """
        Calculate orbital period from semi-major axis.
        
        Args:
            a: Semi-major axis [m]
            mu: Gravitational parameter [m³/s²]
            
        Returns:
            Orbital period [s]
        """
        return TWO_PI * math.sqrt((a ** 3) / mu)
    
    @staticmethod
    def elements_to_state(oe: OrbitalElements, mu: float = MU_EARTH) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert orbital elements to position and velocity vectors (ECI).
        
        Args:
            oe: Orbital elements
            mu: Gravitational parameter [m³/s²]
            
        Returns:
            Tuple of (position [m], velocity [m/s]) in ECI frame
        """
        a, e, i, raan, omega, M = oe.a, oe.e, oe.i, oe.raan, oe.omega, oe.M
        
        # Solve Kepler's equation
        E = OrbitalMechanics.solve_kepler(M, e)
        
        # True anomaly
        nu = OrbitalMechanics.eccentric_to_true_anomaly(E, e)
        
        # Distance
        r = a * (1 - e * math.cos(E))
        
        # Position and velocity in orbital plane (perifocal frame)
        p = a * (1 - e * e)  # Semi-latus rectum
        
        # Position in perifocal frame
        r_pf = np.array([
            r * math.cos(nu),
            r * math.sin(nu),
            0.0
        ])
        
        # Velocity in perifocal frame
        h = math.sqrt(mu * p)  # Specific angular momentum
        v_pf = np.array([
            -mu / h * math.sin(nu),
            mu / h * (e + math.cos(nu)),
            0.0
        ])
        
        # Rotation matrix from perifocal to ECI
        cos_raan, sin_raan = math.cos(raan), math.sin(raan)
        cos_omega, sin_omega = math.cos(omega), math.sin(omega)
        cos_i, sin_i = math.cos(i), math.sin(i)
        
        # Combined rotation matrix
        R = np.array([
            [cos_raan * cos_omega - sin_raan * sin_omega * cos_i,
             -cos_raan * sin_omega - sin_raan * cos_omega * cos_i,
             sin_raan * sin_i],
            [sin_raan * cos_omega + cos_raan * sin_omega * cos_i,
             -sin_raan * sin_omega + cos_raan * cos_omega * cos_i,
             -cos_raan * sin_i],
            [sin_omega * sin_i,
             cos_omega * sin_i,
             cos_i]
        ])
        
        # Transform to ECI
        r_eci = R @ r_pf
        v_eci = R @ v_pf
        
        return r_eci, v_eci
    
    @staticmethod
    def state_to_elements(r: np.ndarray, v: np.ndarray, 
                          epoch: float = 0.0, mu: float = MU_EARTH) -> OrbitalElements:
        """
        Convert position and velocity to orbital elements.
        
        Args:
            r: Position vector [m] in ECI
            v: Velocity vector [m/s] in ECI
            epoch: Epoch in MJD2000
            mu: Gravitational parameter [m³/s²]
            
        Returns:
            OrbitalElements
        """
        r_mag = np.linalg.norm(r)
        v_mag = np.linalg.norm(v)
        
        # Specific angular momentum
        h = np.cross(r, v)
        h_mag = np.linalg.norm(h)
        
        # Node vector
        K = np.array([0, 0, 1])
        n = np.cross(K, h)
        n_mag = np.linalg.norm(n)
        
        # Eccentricity vector
        e_vec = ((v_mag**2 - mu/r_mag) * r - np.dot(r, v) * v) / mu
        e = np.linalg.norm(e_vec)
        
        # Specific energy
        energy = v_mag**2 / 2 - mu / r_mag
        
        # Semi-major axis
        if abs(e - 1.0) > 1e-10:
            a = -mu / (2 * energy)
        else:
            a = float('inf')  # Parabolic
        
        # Inclination
        i = math.acos(np.clip(h[2] / h_mag, -1, 1))
        
        # RAAN
        if n_mag > 1e-10:
            raan = math.acos(np.clip(n[0] / n_mag, -1, 1))
            if n[1] < 0:
                raan = TWO_PI - raan
        else:
            raan = 0.0
        
        # Argument of periapsis
        if n_mag > 1e-10 and e > 1e-10:
            omega = math.acos(np.clip(np.dot(n, e_vec) / (n_mag * e), -1, 1))
            if e_vec[2] < 0:
                omega = TWO_PI - omega
        else:
            omega = 0.0
        
        # True anomaly
        if e > 1e-10:
            nu = math.acos(np.clip(np.dot(e_vec, r) / (e * r_mag), -1, 1))
            if np.dot(r, v) < 0:
                nu = TWO_PI - nu
        else:
            nu = 0.0
        
        # Mean anomaly from true anomaly
        if e < 1.0:
            E = 2 * math.atan2(
                math.sqrt(1 - e) * math.sin(nu / 2),
                math.sqrt(1 + e) * math.cos(nu / 2)
            )
            M = E - e * math.sin(E)
            M = M % TWO_PI
        else:
            M = 0.0
        
        return OrbitalElements(a=a, e=e, i=i, raan=raan, omega=omega, M=M, epoch=epoch)
    
    @staticmethod
    def propagate(oe: OrbitalElements, dt: float, mu: float = MU_EARTH) -> OrbitalElements:
        """
        Propagate orbital elements forward in time (Keplerian motion).
        
        Args:
            oe: Initial orbital elements
            dt: Time step [s]
            mu: Gravitational parameter [m³/s²]
            
        Returns:
            New orbital elements at t + dt
        """
        n = OrbitalMechanics.mean_motion(oe.a, mu)
        
        # New mean anomaly
        M_new = (oe.M + n * dt) % TWO_PI
        
        # New epoch
        epoch_new = oe.epoch + dt / SECONDS_PER_DAY
        
        return OrbitalElements(
            a=oe.a,
            e=oe.e,
            i=oe.i,
            raan=oe.raan,
            omega=oe.omega,
            M=M_new,
            epoch=epoch_new
        )
    
    @staticmethod
    def apply_delta_v(oe: OrbitalElements, delta_v: np.ndarray, 
                      mu: float = MU_EARTH) -> OrbitalElements:
        """
        Apply impulsive delta-V maneuver.
        
        Args:
            oe: Current orbital elements
            delta_v: Delta-V vector [m/s] in ECI
            mu: Gravitational parameter
            
        Returns:
            New orbital elements after maneuver
        """
        # Convert to state vectors
        r, v = OrbitalMechanics.elements_to_state(oe, mu)
        
        # Apply delta-V
        v_new = v + delta_v
        
        # Convert back to orbital elements
        return OrbitalMechanics.state_to_elements(r, v_new, oe.epoch, mu)
    
    @staticmethod
    def get_position_at_epoch(oe: OrbitalElements, epoch: float, 
                               mu: float = MU_EARTH) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get position and velocity at a specific epoch.
        
        Args:
            oe: Orbital elements at reference epoch
            epoch: Target epoch [MJD2000]
            mu: Gravitational parameter
            
        Returns:
            Tuple of (position [m], velocity [m/s])
        """
        dt = (epoch - oe.epoch) * SECONDS_PER_DAY
        oe_new = OrbitalMechanics.propagate(oe, dt, mu)
        return OrbitalMechanics.elements_to_state(oe_new, mu)
    
    @staticmethod 
    def calculate_distance(pos1: np.ndarray, pos2: np.ndarray) -> float:
        """Calculate Euclidean distance between two positions."""
        return float(np.linalg.norm(pos1 - pos2))
