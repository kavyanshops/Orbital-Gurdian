"""
Baseline Agent

No-maneuver baseline for comparison with other agents.
"""

from typing import List, Optional, Dict, Any

from ...agent.base_agent import BaseAgent
from ...api.environment import SpaceEnvironment, Maneuver


class BaselineAgent(BaseAgent):
    """
    Baseline agent that applies no maneuvers.
    Used for comparison with optimization agents.
    """
    
    def __init__(self, environment: SpaceEnvironment):
        super().__init__(environment, name="BaselineAgent")
        
    def optimize(self, **kwargs) -> List[Maneuver]:
        """
        Baseline returns zero-delta-v maneuvers for comparison.
        This shows what happens with no active collision avoidance.
        """
        import numpy as np
        # Create placeholder maneuvers with zero delta-v
        n_maneuvers = kwargs.get('n_maneuvers', 2)
        start_epoch = self.env.start_epoch
        end_epoch = self.env.end_epoch
        time_range = end_epoch - start_epoch
        
        self.maneuvers = []
        for i in range(n_maneuvers):
            epoch = start_epoch + (i + 1) * time_range / (n_maneuvers + 1)
            maneuver = Maneuver(
                epoch=epoch,
                delta_v=np.array([0.0, 0.0, 0.0])  # Zero delta-v (no maneuver)
            )
            self.maneuvers.append(maneuver)
        
        return self.maneuvers
    
    def get_action(self, state: Dict[str, Any]) -> Optional[Maneuver]:
        """Never returns a maneuver."""
        return None
