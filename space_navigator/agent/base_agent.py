"""
Base Agent Class

Abstract base class for all RL agents in the space navigator system.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np

import sys
sys.path.insert(0, str(__file__).rsplit('/', 3)[0])

from space_navigator.api.environment import SpaceEnvironment, Maneuver


class BaseAgent(ABC):
    """
    Abstract base class for maneuver optimization agents.
    """
    
    def __init__(self, environment: SpaceEnvironment, name: str = "BaseAgent"):
        """
        Initialize agent.
        
        Args:
            environment: Space environment to optimize for
            name: Agent name for logging
        """
        self.env = environment
        self.name = name
        self.maneuvers: List[Maneuver] = []
        self.training_history: List[Dict] = []
        
    @abstractmethod
    def optimize(self, **kwargs) -> List[Maneuver]:
        """
        Find optimal maneuver sequence.
        
        Returns:
            List of optimized maneuvers
        """
        pass
    
    @abstractmethod
    def get_action(self, state: Dict[str, Any]) -> Optional[Maneuver]:
        """
        Get action for current state (for online use).
        
        Args:
            state: Current environment state
            
        Returns:
            Maneuver to apply, or None
        """
        pass
    
    def evaluate(self, maneuvers: List[Maneuver]) -> Dict[str, float]:
        """
        Evaluate a maneuver sequence by running simulation.
        
        Args:
            maneuvers: Maneuver sequence to evaluate
            
        Returns:
            Dictionary with evaluation metrics
        """
        from ..simulator.simulator import Simulator
        
        sim = Simulator(self.env, maneuvers)
        summary = sim.run()
        return summary
    
    def save_maneuvers(self, filepath: str):
        """Save optimized maneuvers to CSV."""
        from ..simulator.simulator import Simulator
        Simulator.save_maneuvers(self.maneuvers, filepath)
        
    def get_info(self) -> Dict[str, Any]:
        """Get agent information for logging."""
        return {
            'name': self.name,
            'num_maneuvers': len(self.maneuvers),
            'training_iterations': len(self.training_history)
        }
