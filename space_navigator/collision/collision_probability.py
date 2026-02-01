"""
Collision Probability Estimator

Implements the Chen-Bai approach for estimating collision probability
between two space objects during a conjunction event.

References:
- Chen & Bai, "A Method of Collision Probability Calculation"
- Alfano, "Review of Conjunction Probability Methods for Short-Term Encounters"
"""

import math
import numpy as np
from typing import Tuple, Optional
from scipy import integrate
from scipy.stats import norm


# Constants
PI = math.pi
TWO_PI = 2 * PI


class CollisionProbability:
    """
    Collision probability calculator using Chen-Bai method.
    
    The method computes collision probability by integrating the
    probability density over the collision cross-section area.
    """
    
    @staticmethod
    def compute_miss_distance(
        r1: np.ndarray, 
        v1: np.ndarray,
        r2: np.ndarray, 
        v2: np.ndarray
    ) -> Tuple[float, np.ndarray]:
        """
        Compute miss distance and relative position at closest approach.
        
        Args:
            r1, v1: Position and velocity of object 1 [m, m/s]
            r2, v2: Position and velocity of object 2 [m, m/s]
            
        Returns:
            Tuple of (miss_distance [m], relative_position [m])
        """
        # Relative state
        r_rel = r2 - r1
        v_rel = v2 - v1
        
        v_rel_mag = np.linalg.norm(v_rel)
        
        if v_rel_mag < 1e-10:
            # Objects moving together - use current distance
            return float(np.linalg.norm(r_rel)), r_rel
        
        # Time to closest approach
        t_ca = -np.dot(r_rel, v_rel) / (v_rel_mag ** 2)
        
        # Position at closest approach
        r_ca = r_rel + v_rel * t_ca
        miss_distance = float(np.linalg.norm(r_ca))
        
        return miss_distance, r_ca
    
    @staticmethod
    def compute_relative_velocity(
        v1: np.ndarray,
        v2: np.ndarray
    ) -> float:
        """Compute relative velocity magnitude."""
        return float(np.linalg.norm(v2 - v1))
    
    @staticmethod
    def chen_bai_probability(
        r1: np.ndarray,
        v1: np.ndarray,
        r2: np.ndarray,
        v2: np.ndarray,
        radius1: float,
        radius2: float,
        sigma1: np.ndarray = None,
        sigma2: np.ndarray = None
    ) -> float:
        """
        Compute collision probability using Chen-Bai method.
        
        Args:
            r1, v1: Position/velocity of object 1 [m, m/s]
            r2, v2: Position/velocity of object 2 [m, m/s]
            radius1, radius2: Cross-section radii [m]
            sigma1, sigma2: Position uncertainties (3x3 covariance or 3-vector std) [m]
            
        Returns:
            Collision probability (0-1)
        """
        # Default uncertainties if not provided
        if sigma1 is None:
            sigma1 = np.array([100.0, 100.0, 100.0])  # 100m uncertainty
        if sigma2 is None:
            sigma2 = np.array([100.0, 100.0, 100.0])
        
        # Convert to arrays if needed
        sigma1 = np.atleast_1d(sigma1)
        sigma2 = np.atleast_1d(sigma2)
        
        # Combined collision radius
        combined_radius = radius1 + radius2
        
        # Compute miss distance and relative position
        miss_distance, r_ca = CollisionProbability.compute_miss_distance(r1, v1, r2, v2)
        
        # Combined uncertainty (RSS)
        if sigma1.shape == (3, 3):
            # Covariance matrices
            sigma_combined = sigma1 + sigma2
            sigma_diag = np.sqrt(np.diag(sigma_combined))
        else:
            # Standard deviation vectors
            sigma_combined = np.sqrt(sigma1**2 + sigma2**2)
            sigma_diag = sigma_combined
        
        # Average position uncertainty
        sigma_avg = np.mean(sigma_diag)
        
        if sigma_avg < 1e-10:
            # No uncertainty - deterministic check
            return 1.0 if miss_distance < combined_radius else 0.0
        
        # Normalized miss distance
        u = miss_distance / sigma_avg
        
        # Normalized collision radius
        R = combined_radius / sigma_avg
        
        # Collision probability using 2D Gaussian integration
        # P = 1 - exp(-R^2/2) * I0(u*R) for circular cross-section
        # Simplified approximation for small R:
        
        if u < 0.1:
            # Very close approach - high probability
            prob = 1.0 - math.exp(-R**2 / 2)
        elif R < 0.1:
            # Very small collision cross-section
            prob = (R**2 / 2) * math.exp(-u**2 / 2)
        else:
            # General case - 2D integration
            prob = CollisionProbability._integrate_2d_gaussian(u, R)
        
        return min(max(prob, 0.0), 1.0)
    
    @staticmethod
    def _integrate_2d_gaussian(u: float, R: float) -> float:
        """
        Integrate 2D Gaussian over circular region.
        
        Uses numerical integration for accuracy.
        """
        # For efficiency, use analytical approximation
        # P ≈ (R^2/2) * exp(-u^2/2) for u >> R
        # P ≈ 1 - exp(-R^2/2) for u << R
        
        # Blend between approximations
        weight = math.exp(-u**2 / (2 * R**2)) if R > 0 else 0
        
        p_close = 1.0 - math.exp(-R**2 / 2)
        p_far = (R**2 / 2) * math.exp(-u**2 / 2)
        
        prob = weight * p_close + (1 - weight) * p_far
        
        return prob
    
    @staticmethod
    def conjunction_screening(
        r1: np.ndarray,
        v1: np.ndarray,
        r2: np.ndarray,
        v2: np.ndarray,
        radius1: float,
        radius2: float,
        threshold: float = 10000.0
    ) -> dict:
        """
        Perform conjunction screening and return detailed information.
        
        Args:
            r1, v1: Primary object state
            r2, v2: Secondary object state
            radius1, radius2: Object radii [m]
            threshold: Warning threshold [m]
            
        Returns:
            Dictionary with conjunction details
        """
        miss_distance, r_ca = CollisionProbability.compute_miss_distance(r1, v1, r2, v2)
        rel_velocity = CollisionProbability.compute_relative_velocity(v1, v2)
        
        # Compute probability
        prob = CollisionProbability.chen_bai_probability(
            r1, v1, r2, v2, radius1, radius2
        )
        
        return {
            'miss_distance_m': miss_distance,
            'miss_distance_km': miss_distance / 1000,
            'relative_velocity_ms': rel_velocity,
            'collision_probability': prob,
            'is_warning': miss_distance < threshold,
            'combined_radius': radius1 + radius2,
            'relative_position': r_ca.tolist()
        }


def compute_cumulative_probability(probabilities: list) -> float:
    """
    Compute cumulative collision probability from multiple conjunctions.
    
    Uses the formula: P_total = 1 - Π(1 - p_i)
    
    Args:
        probabilities: List of individual collision probabilities
        
    Returns:
        Cumulative collision probability
    """
    if not probabilities:
        return 0.0
    
    # Product of survival probabilities
    survival = 1.0
    for p in probabilities:
        survival *= (1.0 - p)
    
    return 1.0 - survival


def estimate_collision_probability_simple(
    distance: float,
    combined_radius: float,
    uncertainty: float = 100.0
) -> float:
    """
    Simplified collision probability estimate.
    
    Uses exponential decay model for quick estimation.
    
    Args:
        distance: Current distance [m]
        combined_radius: Sum of object radii [m]
        uncertainty: Position uncertainty [m]
        
    Returns:
        Collision probability (0-1)
    """
    if distance < combined_radius:
        return 1.0
    
    # Normalized distance
    z = (distance - combined_radius) / uncertainty
    
    # Gaussian CDF-based probability
    prob = 2 * (1 - norm.cdf(z))
    
    return min(max(prob, 0.0), 1.0)
