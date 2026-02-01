"""
Table Agent

Agent that loads and applies a pre-defined maneuver table from CSV.
"""

from typing import List, Optional, Dict, Any
import numpy as np

from .base_agent import BaseAgent
from ..api.environment import SpaceEnvironment, Maneuver
from ..simulator.simulator import Simulator


class TableAgent(BaseAgent):
    """
    Agent that applies pre-defined maneuvers from a CSV file.
    """
    
    def __init__(self, environment: SpaceEnvironment, maneuvers_path: Optional[str] = None):
        """
        Initialize table agent.
        
        Args:
            environment: Space environment
            maneuvers_path: Path to maneuvers CSV file
        """
        super().__init__(environment, name="TableAgent")
        
        if maneuvers_path:
            self.maneuvers = Simulator.load_maneuvers(maneuvers_path)
        
    def optimize(self, **kwargs) -> List[Maneuver]:
        """Table agent doesn't optimize - just returns loaded maneuvers."""
        return self.maneuvers
    
    def get_action(self, state: Dict[str, Any]) -> Optional[Maneuver]:
        """Get next maneuver if epoch matches."""
        current_epoch = state['epoch']
        
        for m in self.maneuvers:
            # Check if this maneuver should be applied now
            if abs(m.epoch - current_epoch) < 1e-6:  # Small tolerance
                return m
        
        return None
    
    def set_maneuvers(self, maneuvers: List[Maneuver]):
        """Set maneuver table directly."""
        self.maneuvers = maneuvers
